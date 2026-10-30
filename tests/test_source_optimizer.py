"""Source rewrites must preserve output and avoid formats and used returns."""
import subprocess
import tempfile
from pathlib import Path
from src.compiler.source_optimizer import optimize_c_source


def test_literal_printf_source_preserves_output():
    source = '#include <stdio.h>\nint main(void){printf("hello world "); return 0;}\n'
    result = optimize_c_source(source)
    assert 'fputs("hello world ", stdout)' in result['optimized_source']
    assert result['source_optimization_count'] == 1
    with tempfile.TemporaryDirectory() as directory:
        outputs = []
        for name, code in [('before', source), ('after', result['optimized_source'])]:
            path = Path(directory) / f'{name}.c'
            path.write_text(code)
            binary = Path(directory) / name
            subprocess.run(['clang', str(path), '-o', str(binary)], check=True, capture_output=True)
            run = subprocess.run([str(binary)], check=True, capture_output=True)
            outputs.append((run.stdout, run.returncode))
        assert outputs[0] == outputs[1] == (b'hello world ', 0)


def test_unsupported_calls_and_shadowed_names_unchanged():
    for body in ['return printf("hello");', 'printf("%d", 2); return 0;',
                 'printf("100%%"); return 0;', 'printf("hello\\n"); return 0;',
                 'int stdout=1; printf("hello"); return stdout;']:
        source = '#include <stdio.h>\nint main(void){' + body + '}\n'
        assert optimize_c_source(source)['optimized_source'] == source


def test_macro_calls_unchanged():
    source = '#include <stdio.h>\n#define SAY printf\nint main(void){SAY("hello");return 0;}'
    assert optimize_c_source(source)['optimized_source'] == source
