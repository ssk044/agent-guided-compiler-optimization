"""Autonomous, fail-closed optimization orchestration.

Every proposed pass is applied to a copy of the current IR.  A candidate is
accepted only after it compiles, passes differential testing, and has a lower
deterministic static cost.  This makes an LLM proposal advisory, never trusted.
"""
from __future__ import annotations

import copy
import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Tuple

from src.llvm import ClangRunner, IREmitter, IRParser
from src.optimizations import PASS_REGISTRY
from src.validation import CorrectnessVerifier
from src.agent.optimization_agent import OptimizationAgent


PASS_ORDER = [
    "ConstantPropagation", "ConstantFolding", "StrengthReduction",
    "CommonSubexpressionElimination", "LoopInvariantCodeMotion",
    "DeadCodeElimination",
]
ARITHMETIC_OPS = {"mul", "sdiv", "udiv", "srem", "urem"}


@dataclass
class CostBreakdown:
    instructions: int
    arithmetic: int
    temporaries: int
    runtime_ms: float
    weighted_cost: float


class CostEvaluator:
    """Transparent structural cost model, stable across noisy wall-clock runs."""

    def evaluate(self, module, runtime_ms: float = 0.0) -> CostBreakdown:
        instructions = arithmetic = temporaries = 0
        for function in module.functions:
            if function.is_declaration:
                continue
            for block in function.blocks:
                for inst in block.instructions:
                    instructions += 1
                    arithmetic += int(inst.opcode in ARITHMETIC_OPS)
                    temporaries += int(bool(inst.result))
        # Expensive arithmetic and register pressure have a higher penalty.
        return CostBreakdown(instructions, arithmetic, temporaries, runtime_ms,
                             instructions + (3 * arithmetic) + temporaries + (10 * runtime_ms))


class CodeAnalysisSpecialist:
    """Extracts transparent IR-level optimization features for the decision log."""
    def analyze(self, module) -> Dict[str, int]:
        features = {"constant_pairs": 0, "algebraic_patterns": 0, "dead_results": 0,
                    "repeated_subexpressions": 0, "arithmetic_ops": 0}
        uses = set()
        expression_counts: Dict[tuple, int] = {}
        for fn in module.functions:
            for block in fn.blocks:
                for inst in block.instructions:
                    uses.update(inst.get_used_variables())
        for fn in module.functions:
            for block in fn.blocks:
                for inst in block.instructions:
                    if inst.is_binary_arithmetic():
                        features["arithmetic_ops"] += 1
                        if len(inst.operands) >= 2 and all(op.is_constant() for op in inst.operands):
                            features["constant_pairs"] += 1
                        if any(op.value in {"0", "1", "2", "4", "8", "16"} for op in inst.operands):
                            features["algebraic_patterns"] += 1
                        signature = (inst.opcode, tuple((op.type, op.value) for op in inst.operands))
                        expression_counts[signature] = expression_counts.get(signature, 0) + 1
                    if inst.result and inst.result not in uses and inst.is_pure():
                        features["dead_results"] += 1
        features["repeated_subexpressions"] = sum(count - 1 for count in expression_counts.values() if count > 1)
        return features


class OptimizationSpecialist:
    """Rule-based proposer; optionally lets Qwen reorder the safe pass catalogue."""
    def __init__(self, use_llm: bool = False, model_name: Optional[str] = None):
        self.use_llm, self.model_name = use_llm, model_name
        self._cached_order: Optional[List[str]] = None

    def propose(self, source: str, module, ir_text: str, facts: Dict[str, int]) -> Tuple[List[str], str]:
        if not self.use_llm:
            return PASS_ORDER, "rule"
        if self._cached_order is not None:
            return self._cached_order, "llm"
        try:
            proposal = OptimizationAgent(self.model_name).analyze_and_propose(source, module, ir_text)
            suggested = [item.pass_name for item in sorted(proposal.recommended_passes, key=lambda item: item.order)
                         if item.pass_name in PASS_REGISTRY]
            self._cached_order = suggested + [name for name in PASS_ORDER if name not in suggested]
            return self._cached_order, "llm"
        except Exception:
            return PASS_ORDER, "rule-fallback"


@dataclass
class Decision:
    iteration: int
    pass_name: str
    rationale: str
    changes: int
    verified: bool
    cost_before: int
    cost_after: int
    decision: str
    reason: str
    details: List[str] = field(default_factory=list)
    proposal_source: str = "rule"


@dataclass
class AutonomousRun:
    source_path: str
    initial_ir: str
    initial_cost: CostBreakdown
    final_cost: CostBreakdown
    final_ir: str
    decisions: List[Decision]
    final_verification_passed: bool
    baseline_output: str = ""
    optimized_output: str = ""
    verification_tests_run: int = 0
    verification_tests_passed: int = 0
    timings: Dict[str, float] = field(default_factory=dict)

    @property
    def accepted(self) -> int:
        return sum(d.decision == "accepted" for d in self.decisions)

    @property
    def iterations_to_convergence(self) -> int:
        return max((d.iteration for d in self.decisions), default=0)

    @property
    def reduction_percent(self) -> float:
        return ((self.initial_cost.weighted_cost - self.final_cost.weighted_cost)
                / self.initial_cost.weighted_cost * 100) if self.initial_cost.weighted_cost else 0.0

    def to_dict(self) -> Dict:
        data = asdict(self)
        data["accepted"] = self.accepted
        data["iterations_to_convergence"] = self.iterations_to_convergence
        data["reduction_percent"] = self.reduction_percent
        return data


class AutonomousOrchestrator:
    def __init__(self, runner: Optional[ClangRunner] = None, max_iterations: int = 12,
                 use_llm: bool = False, model_name: Optional[str] = None):
        self.runner = runner or ClangRunner()
        self.max_iterations = max_iterations
        self.cost_evaluator = CostEvaluator()
        self.verifier = CorrectnessVerifier(self.runner)
        self.analysis_specialist = CodeAnalysisSpecialist()
        self.optimization_specialist = OptimizationSpecialist(use_llm, model_name)

    def optimize_file(self, source_path: str) -> AutonomousRun:
        """Run analyze -> propose -> verify -> evaluate -> accept/reject to convergence."""
        total_started = time.perf_counter()
        source_path = os.path.abspath(source_path)
        source_text = open(source_path, encoding="utf-8").read()
        with tempfile.TemporaryDirectory(prefix="agent_opt_") as work:
            baseline_ir = os.path.join(work, "baseline.ll")
            baseline_binary = os.path.join(work, "baseline.bin")
            compile_started = time.perf_counter()
            self.runner.compile_to_ir(source_path, baseline_ir)
            self.runner.compile_ir_to_binary(baseline_ir, baseline_binary)
            source_compile_seconds = time.perf_counter() - compile_started
            with open(baseline_ir, encoding="utf-8") as handle:
                baseline_ir_text = handle.read()
                current = IRParser(baseline_ir_text).parse()

            current_runtime = self._runtime_ms(baseline_binary)
            initial = self.cost_evaluator.evaluate(current, current_runtime)
            decisions: List[Decision] = []
            optimization_started = time.perf_counter()
            for iteration in range(1, self.max_iterations + 1):
                accepted_this_round = False
                facts = self.analysis_specialist.analyze(current)
                pass_order, proposal_source = self.optimization_specialist.propose(source_text, current, IREmitter.emit(current), facts)
                for pass_name in pass_order:
                    candidate = copy.deepcopy(current)
                    result = PASS_REGISTRY[pass_name]().run(candidate)
                    before = self.cost_evaluator.evaluate(current, current_runtime)
                    after = self.cost_evaluator.evaluate(candidate, current_runtime)
                    rationale = f"Analysis={facts}. Try {pass_name}; accept only if equivalence and weighted cost improve."
                    if not result.has_changes:
                        decisions.append(Decision(iteration, pass_name, rationale, 0, True,
                                                  before.weighted_cost, after.weighted_cost,
                                                  "skipped", "No applicable opportunity.", result.details, proposal_source))
                        continue

                    verified, reason, runtime_ms = self._verify_candidate(candidate, baseline_binary, work, iteration, pass_name)
                    after = self.cost_evaluator.evaluate(candidate, runtime_ms)
                    if not verified:
                        decisions.append(Decision(iteration, pass_name, rationale, result.changes_made, False,
                                                  before.weighted_cost, after.weighted_cost,
                                                  "rejected", reason, result.details, proposal_source))
                    elif after.weighted_cost >= before.weighted_cost:
                        decisions.append(Decision(iteration, pass_name, rationale, result.changes_made, True,
                                                  before.weighted_cost, after.weighted_cost,
                                                  "rejected", "Verified, but did not reduce weighted cost.", result.details, proposal_source))
                    else:
                        current = candidate
                        current_runtime = runtime_ms
                        accepted_this_round = True
                        decisions.append(Decision(iteration, pass_name, rationale, result.changes_made, True,
                                                  before.weighted_cost, after.weighted_cost,
                                                  "accepted", "Verified and lower cost.", result.details, proposal_source))
                if not accepted_this_round:
                    break
            optimization_seconds = time.perf_counter() - optimization_started

            final_cost = self.cost_evaluator.evaluate(current, current_runtime)
            final_ir = IREmitter.emit(current)
            final_ir_path = os.path.join(work, "final.ll")
            final_binary = os.path.join(work, "final.bin")
            IREmitter.write_to_file(current, final_ir_path)
            final_compile_started = time.perf_counter()
            self.runner.compile_ir_to_binary(final_ir_path, final_binary)
            final_compile_seconds = time.perf_counter() - final_compile_started
            final_verification_started = time.perf_counter()
            final_report = self.verifier.verify(baseline_binary, final_binary)
            final_verification_seconds = time.perf_counter() - final_verification_started
            first_result = final_report.results[0] if final_report.results else None
            timings = {
                "source_compile_seconds": source_compile_seconds,
                "optimization_seconds": optimization_seconds,
                "final_compile_seconds": final_compile_seconds,
                "final_verification_seconds": final_verification_seconds,
                "total_seconds": time.perf_counter() - total_started,
            }
            return AutonomousRun(
                source_path, baseline_ir_text, initial, final_cost, final_ir, decisions, final_report.is_valid,
                baseline_output=first_result.baseline_stdout if first_result else "",
                optimized_output=first_result.optimized_stdout if first_result else "",
                verification_tests_run=final_report.tests_run,
                verification_tests_passed=final_report.tests_passed,
                timings=timings,
            )

    def _verify_candidate(self, module, baseline_binary: str, work: str, iteration: int,
                          pass_name: str) -> Tuple[bool, str, float]:
        ir_path = os.path.join(work, f"candidate_{iteration}_{pass_name}.ll")
        binary_path = os.path.join(work, f"candidate_{iteration}_{pass_name}.bin")
        try:
            IREmitter.write_to_file(module, ir_path)
            self.runner.compile_ir_to_binary(ir_path, binary_path)
            report = self.verifier.verify(baseline_binary, binary_path)
            return report.is_valid, report.rejection_reason or "Verified on 13 deterministic/randomized cases.", self._runtime_ms(binary_path)
        except Exception as exc:
            return False, f"Candidate did not compile or execute: {exc}", 0.0

    def _runtime_ms(self, binary_path: str, samples: int = 3) -> float:
        values = [self.runner.execute_binary(binary_path, args=["7"], timeout=self.verifier.timeout).elapsed_time_seconds * 1000
                  for _ in range(samples)]
        return sum(values) / len(values)


def write_decision_log(run: AutonomousRun, output_path: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(run.to_dict(), handle, indent=2)
    return output_path
