"""
Correctness Verifier and Differential Testing Harness.
Ensures optimized binaries strictly match baseline program output across test cases.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import random
from src.llvm.clang_runner import ClangRunner, ExecutionResult


@dataclass
class TestCaseResult:
    input_desc: str
    passed: bool
    baseline_stdout: str
    optimized_stdout: str
    baseline_exit_code: int
    optimized_exit_code: int
    error_message: Optional[str] = None


@dataclass
class VerificationReport:
    is_valid: bool
    tests_run: int
    tests_passed: int
    rejection_reason: Optional[str] = None
    results: List[TestCaseResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        return (self.tests_passed / self.tests_run * 100.0) if self.tests_run > 0 else 0.0


class CorrectnessVerifier:
    def __init__(self, runner: Optional[ClangRunner] = None, timeout: float = 5.0):
        self.runner = runner or ClangRunner()
        self.timeout = timeout

    def verify(
        self,
        baseline_binary: str,
        optimized_binary: str,
        test_inputs: Optional[List[Dict[str, Any]]] = None
    ) -> VerificationReport:
        """
        Runs differential tests comparing outputs and exit codes of baseline vs optimized binaries.
        """
        # Default test inputs if none provided
        if not test_inputs:
            rng = random.Random(20261006)
            test_inputs = [
                {"desc": "Default run", "args": [], "stdin": None},
                *[{"desc": f"Random arg {i + 1}: {value}", "args": [str(value)], "stdin": None}
                  for i, value in enumerate([0, 1, -1] + [rng.randint(-1000, 1000) for _ in range(9)])],
            ]

        results: List[TestCaseResult] = []
        tests_passed = 0
        rejection_reason = None

        for test in test_inputs:
            args = test.get("args", [])
            stdin_val = test.get("stdin")
            desc = test.get("desc", f"Args: {args}")

            base_res = self.runner.execute_binary(baseline_binary, args=args, stdin_input=stdin_val, timeout=self.timeout)
            opt_res = self.runner.execute_binary(optimized_binary, args=args, stdin_input=stdin_val, timeout=self.timeout)

            # Check for timeouts
            if opt_res.timed_out:
                rejection_reason = f"Optimized binary timed out ({self.timeout}s) on input '{desc}'"
                results.append(TestCaseResult(
                    input_desc=desc,
                    passed=False,
                    baseline_stdout=base_res.stdout,
                    optimized_stdout=opt_res.stdout,
                    baseline_exit_code=base_res.returncode,
                    optimized_exit_code=opt_res.returncode,
                    error_message=rejection_reason
                ))
                break

            # Check exit codes
            if base_res.returncode != opt_res.returncode:
                rejection_reason = f"Exit code mismatch on '{desc}': expected {base_res.returncode}, got {opt_res.returncode}"
                results.append(TestCaseResult(
                    input_desc=desc,
                    passed=False,
                    baseline_stdout=base_res.stdout,
                    optimized_stdout=opt_res.stdout,
                    baseline_exit_code=base_res.returncode,
                    optimized_exit_code=opt_res.returncode,
                    error_message=rejection_reason
                ))
                break

            # Check stdout equality
            if not self._compare_outputs(base_res.stdout, opt_res.stdout):
                rejection_reason = f"Standard output mismatch on '{desc}'\nExpected: {base_res.stdout.strip()}\nGot:      {opt_res.stdout.strip()}"
                results.append(TestCaseResult(
                    input_desc=desc,
                    passed=False,
                    baseline_stdout=base_res.stdout,
                    optimized_stdout=opt_res.stdout,
                    baseline_exit_code=base_res.returncode,
                    optimized_exit_code=opt_res.returncode,
                    error_message=rejection_reason
                ))
                break

            tests_passed += 1
            results.append(TestCaseResult(
                input_desc=desc,
                passed=True,
                baseline_stdout=base_res.stdout,
                optimized_stdout=opt_res.stdout,
                baseline_exit_code=base_res.returncode,
                optimized_exit_code=opt_res.returncode
            ))

        is_valid = (tests_passed == len(test_inputs)) and (rejection_reason is None)
        return VerificationReport(
            is_valid=is_valid,
            tests_run=len(results),
            tests_passed=tests_passed,
            rejection_reason=rejection_reason,
            results=results
        )

    def _compare_outputs(self, out_base: str, out_opt: str) -> bool:
        if out_base == out_opt:
            return True

        # Normalized strip check
        if out_base.strip() == out_opt.strip():
            return True

        # Number-by-number float tolerance check
        import re
        tokens_base = re.findall(r"[-+]?(?:\d*\.\d+|\d+)", out_base)
        tokens_opt = re.findall(r"[-+]?(?:\d*\.\d+|\d+)", out_opt)

        if tokens_base and len(tokens_base) == len(tokens_opt):
            try:
                for b_tok, o_tok in zip(tokens_base, tokens_opt):
                    b_val = float(b_tok)
                    o_val = float(o_tok)
                    if abs(b_val - o_val) > 1e-5:
                        return False
                return True
            except ValueError:
                pass

        return False
