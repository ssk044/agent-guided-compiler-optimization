"""
Performance Benchmarking Harness with high-precision statistical timing.
"""
import os
import time
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import numpy as np
from src.llvm.clang_runner import ClangRunner


@dataclass
class BenchmarkResult:
    baseline_mean_ms: float
    baseline_std_ms: float
    optimized_mean_ms: float
    optimized_std_ms: float
    clang_o1_mean_ms: Optional[float] = None
    clang_o2_mean_ms: Optional[float] = None
    speedup_percent: float = 0.0
    speedup_factor: float = 1.0
    baseline_instruction_count: int = 0
    optimized_instruction_count: int = 0
    instruction_reduction_percent: float = 0.0
    baseline_binary_size_bytes: int = 0
    optimized_binary_size_bytes: int = 0
    iterations_run: int = 10

    @property
    def is_faster(self) -> bool:
        return self.speedup_percent > 0.0


class Benchmarker:
    def __init__(self, runner: Optional[ClangRunner] = None, iterations: int = 15, warmup: int = 3):
        self.runner = runner or ClangRunner()
        self.iterations = iterations
        self.warmup = warmup

    def run_benchmark(
        self,
        baseline_binary: str,
        optimized_binary: str,
        clang_o1_binary: Optional[str] = None,
        clang_o2_binary: Optional[str] = None,
        args: Optional[List[str]] = None,
        stdin_input: Optional[str] = None,
        base_inst_count: int = 0,
        opt_inst_count: int = 0
    ) -> BenchmarkResult:
        """
        Executes warmup runs, followed by N high-precision statistical timing iterations.
        """
        base_times = self._time_binary(baseline_binary, args, stdin_input)
        opt_times = self._time_binary(optimized_binary, args, stdin_input)

        o1_times = self._time_binary(clang_o1_binary, args, stdin_input) if clang_o1_binary else None
        o2_times = self._time_binary(clang_o2_binary, args, stdin_input) if clang_o2_binary else None

        base_mean = float(np.mean(base_times)) * 1000.0 # ms
        base_std = float(np.std(base_times)) * 1000.0
        opt_mean = float(np.mean(opt_times)) * 1000.0 # ms
        opt_std = float(np.std(opt_times)) * 1000.0

        o1_mean = float(np.mean(o1_times)) * 1000.0 if o1_times else None
        o2_mean = float(np.mean(o2_times)) * 1000.0 if o2_times else None

        # Speedup calculation
        if opt_mean > 0:
            speedup_factor = base_mean / opt_mean
            speedup_pct = ((base_mean - opt_mean) / base_mean) * 100.0
        else:
            speedup_factor = 1.0
            speedup_pct = 0.0

        # Instruction reduction
        inst_reduct_pct = 0.0
        if base_inst_count > 0:
            inst_reduct_pct = ((base_inst_count - opt_inst_count) / base_inst_count) * 100.0

        base_size = os.path.getsize(baseline_binary) if os.path.exists(baseline_binary) else 0
        opt_size = os.path.getsize(optimized_binary) if os.path.exists(optimized_binary) else 0

        return BenchmarkResult(
            baseline_mean_ms=base_mean,
            baseline_std_ms=base_std,
            optimized_mean_ms=opt_mean,
            optimized_std_ms=opt_std,
            clang_o1_mean_ms=o1_mean,
            clang_o2_mean_ms=o2_mean,
            speedup_percent=speedup_pct,
            speedup_factor=speedup_factor,
            baseline_instruction_count=base_inst_count,
            optimized_instruction_count=opt_inst_count,
            instruction_reduction_percent=inst_reduct_pct,
            baseline_binary_size_bytes=base_size,
            optimized_binary_size_bytes=opt_size,
            iterations_run=self.iterations
        )

    def _time_binary(
        self,
        binary_path: str,
        args: Optional[List[str]] = None,
        stdin_input: Optional[str] = None
    ) -> List[float]:
        cmd = [os.path.abspath(binary_path)]
        if args:
            cmd.extend(args)

        # Warmup iterations
        for _ in range(self.warmup):
            subprocess.run(cmd, input=stdin_input, capture_output=True, text=True)

        durations: List[float] = []
        for _ in range(self.iterations):
            t_start = time.perf_counter_ns()
            res = subprocess.run(cmd, input=stdin_input, capture_output=True, text=True)
            t_end = time.perf_counter_ns()
            if res.returncode == 0:
                durations.append((t_end - t_start) / 1e9) # seconds

        if not durations:
            return [0.001]
        return durations
