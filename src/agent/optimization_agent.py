"""
LLM-Guided Compiler Optimization Agent.
Analyzes IR and program structure, identifies optimization candidates,
and outputs verified structured proposals.
"""
import json
import logging
from typing import Dict, Any, List, Optional
from src.agent.schema import OptimizationProposal, OptimizationOpportunity, PassRecommendation
from src.agent.ollama_client import OllamaClient
from src.llvm.ir_nodes import IRModule
from src.analysis.cfg import ControlFlowGraph
from src.analysis.dominators import DominatorAnalysis
from src.analysis.loop_analysis import LoopAnalysis
from src.analysis.dataflow import DefUseAnalysis, MemoryTracker
from src.optimizations.base import PassManager
from src.optimizations import (
    ConstantFoldingPass, ConstantPropagationPass,
    DeadCodeEliminationPass, CommonSubexpressionEliminationPass,
    StrengthReductionPass, LoopInvariantCodeMotionPass,
    PASS_REGISTRY
)

logger = logging.getLogger(__name__)


class OptimizationAgent:
    def __init__(self, model_name: Optional[str] = None):
        self.client = OllamaClient(requested_model=model_name)
        self.active_model = self.client.active_model

    def analyze_and_propose(
        self,
        c_source: str,
        ir_module: IRModule,
        ir_text: str
    ) -> OptimizationProposal:
        """
        Extracts program metrics, prepares context, prompts LLM Agent,
        and returns validated OptimizationProposal.
        """
        # 1. Gather compiler analysis facts
        facts = self._gather_analysis_facts(ir_module)

        # 2. If Ollama is available, query the LLM
        if self.client.is_available():
            try:
                return self._query_llm(c_source, ir_text, facts)
            except Exception as e:
                logger.warning(f"Ollama inference encountered error: {e}. Falling back to rule-guided static proposal.")

        # 3. Fallback: synthesize proposal from verified formal compiler analysis
        return self._generate_heuristic_proposal(facts)

    def _gather_analysis_facts(self, module: IRModule) -> Dict[str, Any]:
        facts = {
            "functions": [],
            "total_instructions": module.total_instructions,
            "detected_candidates": []
        }

        for func in module.functions:
            if func.is_declaration:
                continue

            cfg = ControlFlowGraph(func)
            dom = DominatorAnalysis(cfg)
            loops = LoopAnalysis(cfg, dom)
            defuse = DefUseAnalysis(func)
            mem = MemoryTracker(func)

            fn_data = {
                "name": func.name,
                "blocks": len(func.blocks),
                "instructions": func.total_instructions,
                "loops": len(loops.loops),
                "allocas": len(mem.allocas),
                "dead_regs": [r for r in defuse.def_to_uses if defuse.is_dead(r)]
            }
            facts["functions"].append(fn_data)

            # Detect candidate patterns
            for block in func.blocks:
                for inst in block.instructions:
                    if inst.is_binary_arithmetic() and len(inst.operands) >= 2:
                        c1 = inst.operands[0].is_constant()
                        c2 = inst.operands[1].is_constant()
                        if c1 and c2:
                            facts["detected_candidates"].append({
                                "type": "ConstantFolding",
                                "func": func.name,
                                "block": block.name,
                                "inst": inst.render().strip()
                            })
                        elif (c1 or c2) and inst.opcode == "mul":
                            facts["detected_candidates"].append({
                                "type": "StrengthReduction",
                                "func": func.name,
                                "block": block.name,
                                "inst": inst.render().strip()
                            })

            # Check loop invariants
            for l in loops.loops:
                invariants = loops.find_loop_invariants(l)
                if invariants:
                    facts["detected_candidates"].append({
                        "type": "LoopInvariantCodeMotion",
                        "func": func.name,
                        "block": l.header,
                        "inst": f"{len(invariants)} invariant op(s)"
                    })

        return facts

    def _query_llm(self, c_source: str, ir_text: str, facts: Dict[str, Any]) -> OptimizationProposal:
        system_prompt = (
            "You are an expert LLM Compiler Optimization Agent. "
            "Your task is to analyze C source code, LLVM IR, Control-Flow Graphs, and Data-flow analysis facts "
            "to formulate a structured, mathematically sound compiler optimization plan.\n"
            "You MUST respond ONLY with valid JSON conforming strictly to the requested schema.\n"
            "Available Optimization Passes:\n"
            "- ConstantFolding: evaluate constant expressions at compile time\n"
            "- ConstantPropagation: propagate constants across memory allocas and registers\n"
            "- DeadCodeElimination: eliminate unreferenced pure instructions, dead stores, and unused allocas\n"
            "- CommonSubexpressionElimination: eliminate redundant identical calculations\n"
            "- StrengthReduction: replace costly mul/div by powers of 2 with bitwise shifts\n"
            "- LoopInvariantCodeMotion: hoist computations that do not vary across loop iterations into preheaders"
        )

        user_prompt = f"""
Analyze this program and produce an optimization proposal:

=== C SOURCE CODE ===
{c_source}

=== LLVM IR (Unoptimized) ===
{ir_text[:1000]}

=== COMPILER ANALYSIS FACTS ===
Functions: {json.dumps(facts['functions'], indent=2)}
Detected Candidates: {json.dumps(facts['detected_candidates'], indent=2)}

Produce a JSON response matching this schema:
{{
  "summary": "<High-level explanation of optimization opportunities>",
  "opportunities": [
    {{
      "name": "<PassName>",
      "target_function": "<@function_name>",
      "target_block": "<block_name or null>",
      "target_instruction": "<instruction or null>",
      "rationale": "<Mathematical/compiler reasoning for correctness and benefit>",
      "confidence": <float 0.0 to 1.0>
    }}
  ],
  "recommended_passes": [
    {{
      "pass_name": "<PassName>",
      "order": 1,
      "parameters": {{}},
      "reason": "<Why run this pass in this order>"
    }}
  ],
  "loop_optimizations": "<Optional loop transformations advice>",
  "expected_speedup_estimate": <float, e.g. 1.15>,
  "safety_assessment": "<Verification reasoning preserving semantic equivalence>"
}}
"""
        json_data = self.client.generate_structured_json(system_prompt, user_prompt)
        return OptimizationProposal.model_validate(json_data)

    def _generate_heuristic_proposal(self, facts: Dict[str, Any]) -> OptimizationProposal:
        """Constructs an OptimizationProposal from deterministic compiler analysis facts."""
        opportunities = []
        for c in facts.get("detected_candidates", []):
            opportunities.append(OptimizationOpportunity(
                name=c["type"],
                target_function=f"@{c['func']}",
                target_block=c.get("block"),
                target_instruction=c.get("inst"),
                rationale=f"Formal analysis identified {c['type']} candidate at {c.get('inst')}",
                confidence=0.95
            ))

        # Standard sound compiler pass ordering
        pipeline = [
            PassRecommendation(pass_name="ConstantPropagation", order=1, parameters={}, reason="Propagate constants to expose downstream fold opportunities"),
            PassRecommendation(pass_name="ConstantFolding", order=2, parameters={}, reason="Evaluate compile-time arithmetic"),
            PassRecommendation(pass_name="StrengthReduction", order=3, parameters={}, reason="Lower expensive multiplications to bitwise shifts"),
            PassRecommendation(pass_name="CommonSubexpressionElimination", order=4, parameters={}, reason="Remove redundant subexpressions exposed by folding"),
            PassRecommendation(pass_name="LoopInvariantCodeMotion", order=5, parameters={}, reason="Hoist invariant computations out of hot loops"),
            PassRecommendation(pass_name="DeadCodeElimination", order=6, parameters={}, reason="Clean up dead allocas and eliminated expressions")
        ]

        return OptimizationProposal(
            summary=f"Analysis of {len(facts.get('functions', []))} function(s) identified {len(opportunities)} optimization opportunity(ies). Recommended multi-stage transformation pipeline.",
            opportunities=opportunities,
            recommended_passes=pipeline,
            loop_optimizations="Hoist loop invariant calculations to preheader and lower inner multiplications to bitwise shifts.",
            expected_speedup_estimate=1.20,
            safety_assessment="All transformations preserve bitwise arithmetic semantics, variable lifetimes, and loop iteration bounds."
        )

    def build_pass_pipeline(self, proposal: OptimizationProposal) -> PassManager:
        """Builds a PassManager instance configured according to the proposal's recommendations."""
        pm = PassManager()
        # Sort recommendations by order
        sorted_recs = sorted(proposal.recommended_passes, key=lambda p: p.order)
        for rec in sorted_recs:
            pass_cls = PASS_REGISTRY.get(rec.pass_name)
            if pass_cls:
                pm.add_pass(pass_cls())
        return pm
