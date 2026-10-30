"""Terminal access to native C and Python compilation, without custom IR limits."""
from pathlib import Path
import subprocess
import sys
import tempfile

from rich.console import Console
from rich.syntax import Syntax

from src.compiler import compile_python
from src.compiler.artifacts import save_c_artifacts
from src.compiler.c_backend import compile_native_c, execute_ir_pair


def compile_native_file(path, *, language='C', level='-O2', python_level=0,
                        report_path=None, show_output=None, stdin_input='', timeout=5):
    path = Path(path)
    source = path.read_text(encoding='utf-8')
    console = Console()
    from datetime import datetime
    report = Path(report_path) if report_path else Path('reports/runs') / (
        path.stem + '_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f')) / 'REPORT.md'
    report.parent.mkdir(parents=True, exist_ok=True)
    artifacts = report.parent / (report.stem + '_artifacts')
    artifacts.mkdir(exist_ok=True)
    if language == 'Python':
        before = compile_python(source, 0, str(path))
        result = compile_python(source, python_level, str(path))
        views = [('Original Python', source, 'python'), ('Bytecode before (level 0)', before.bytecode_listing, 'text'),
                 (f'Bytecode after (level {python_level})', result.bytecode_listing, 'text')]
        (artifacts / 'program.pyc').write_bytes(result.pyc_bytes)
        (artifacts / 'original.py').write_text(source, encoding='utf-8')
        (artifacts / 'before.bytecode.txt').write_text(before.bytecode_listing, encoding='utf-8')
        (artifacts / 'after.bytecode.txt').write_text(result.bytecode_listing, encoding='utf-8')
        note = ('CPython bytecode compilation. No LLVM/TAC or custom cost score applies. '
                'Level 1 removes asserts; level 2 also removes docstrings. '
                'This does not automatically accelerate arbitrary Python algorithms. '
                f'Compilation took {result.compile_seconds:.6f} seconds.')
    else:
        result = compile_native_c(source, level)
        views = [('Original C', source, 'c'), ('LLVM IR before', result['initial_ir'], 'llvm'),
                 ('Optimized LLVM IR', result['code'], 'llvm'),
                 ('Optimized code · assembly', result['optimized_assembly'], 'asm'),
                 ('Optimized C source', result['optimized_source'], 'c')]
        save_c_artifacts(result, artifacts)
        note = result['source_optimization_note'] + ' ' + (f'Native Clang {level}; compiled and linked without executing. '
                'Model guidance, educational TAC and custom cost metrics do not apply. '
                'Differential verification has not been run.')
    console.print(note)
    lines = ['# Native compilation report', note]
    for title, code, syntax in views:
        console.print(title, style='bold cyan')
        console.print(Syntax(code, syntax, word_wrap=True, line_numbers=True))
        lines += ['', f'## {title}', f'`````{syntax}', code, '`````']
    captured_output = {}
    if show_output is None:
        try:
            show_output = console.input('Display program output? [y/N]: ').strip().lower() in ('y', 'yes')
        except EOFError:
            show_output = False
    if show_output:
        if language == 'C':
            outputs = execute_ir_pair(result['initial_ir'], result['code'], stdin_input, timeout)
            for name, execution in outputs.items():
                text = f'Exit: {execution.returncode}\n{execution.stdout}\n{execution.stderr}'
                captured_output[name] = text
                console.print(name)
                console.print(text, markup=False)
                lines += ['', f'## Output {name} (one input)', '`````text', text, '`````']
        else:
            flags = ['-O'] if python_level == 1 else ['-OO'] if python_level == 2 else []
            try:
                execution = subprocess.run([sys.executable, *flags, str(path.resolve())],
                                           input=stdin_input, text=True, capture_output=True,
                                           timeout=timeout, cwd=path.resolve().parent)
                text = f'Exit: {execution.returncode}\n{execution.stdout}\n{execution.stderr}'
            except subprocess.TimeoutExpired:
                text = f'Execution timed out after {timeout} seconds.'
            captured_output['python'] = text
            console.print(text, markup=False)
            lines += ['', '## Program output', '`````text', text, '`````']
    report.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    console.print(f'Report and artifacts: {report.resolve()}', markup=False)
    from src.experiment_history import save_experiment
    if language == 'Python':
        snapshot = dict(language='Python', source=source, code=result.bytecode_listing,
                        baseline_bytecode=before.bytecode_listing, optimization_level=python_level,
                        model='CPython', timings={'source_compile_seconds': result.compile_seconds,
                                                'total_seconds': result.elapsed_seconds})
    else:
        snapshot = result
    snapshot['saved_output'] = captured_output
    save_experiment(snapshot, interface='Terminal', source_name=path.name, report_path=report)
    return report
