"""Native Clang backend for C beyond the educational IR parser's subset.

Compilation never executes the submitted program. Output execution is explicit.
"""
from __future__ import annotations

from pathlib import Path
import tempfile
import time

from src.llvm.clang_runner import ClangRunner


def compile_native_c(source: str, optimization_level: str = '-O2') -> dict:
    if optimization_level not in ('-O1', '-O2', '-O3', '-Os'):
        raise ValueError('Choose -O1, -O2, -O3, or -Os.')
    started = time.perf_counter()
    runner = ClangRunner()
    with tempfile.TemporaryDirectory(prefix='native_c_') as directory:
        root = Path(directory)
        path = root / 'program.c'
        path.write_text(source, encoding='utf-8')
        baseline, optimized = root / 'before.ll', root / 'after.ll'
        runner.compile_to_ir(str(path), str(baseline), opt_level='-O0')
        runner.compile_to_ir(str(path), str(optimized), opt_level=optimization_level)
        # Check that both complete programs link, without executing either one.
        for ir, name in ((baseline, 'before'), (optimized, 'after')):
            runner.compile_ir_to_binary(str(ir), str(root / name), opt_flags=['-lm'])
        elapsed = time.perf_counter() - started
        return dict(language='C', source=source, code=optimized.read_text(), initial_ir=baseline.read_text(),
                    timings=dict(source_compile_seconds=elapsed, optimization_seconds=0.0,
                                 final_compile_seconds=0.0, final_verification_seconds=0.0, total_seconds=elapsed),
                    custom_optimizer=False, backend=f'Clang {optimization_level}', model='Clang native optimizer',
                    verification_passed=None, tests_passed=0, tests_run=0, accepted=0,
                    baseline_output='', optimized_output='', initial_cost=None, final_cost=None,
                    reduction_percent=None, fallback_reason='', extension='ll', mime='text/plain',
                    output_label=f'Clang {optimization_level} LLVM IR')


def execute_ir_pair(before: str, after: str, stdin_input: str = '', timeout: float = 5) -> dict:
    runner = ClangRunner()
    outputs = {}
    with tempfile.TemporaryDirectory(prefix='native_c_output_') as directory:
        for name, ir in (('before', before), ('after', after)):
            path = Path(directory) / f'{name}.ll'
            path.write_text(ir, encoding='utf-8')
            binary = Path(directory) / name
            runner.compile_ir_to_binary(str(path), str(binary), opt_flags=['-lm'])
            outputs[name] = runner.execute_binary(str(binary), stdin_input=stdin_input, timeout=timeout)
    return outputs
