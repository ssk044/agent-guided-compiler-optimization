"""Generate code from the final IR and persist editor-friendly compiler outputs."""
from pathlib import Path
import tempfile

from src.llvm.clang_runner import ClangRunner


def assembly_from_ir(ir: str) -> str:
    """Lower exactly the displayed final IR, without another IR optimization pass."""
    with tempfile.TemporaryDirectory(prefix='compiler_assembly_') as directory:
        root = Path(directory)
        path = root / 'optimized.ll'
        path.write_text(ir, encoding='utf-8')
        output = root / 'optimized.s'
        ClangRunner().compile_ir_to_assembly(str(path), str(output))
        return output.read_text(encoding='utf-8')


def save_c_artifacts(result: dict, directory) -> Path:
    """Keep each run in its own directory so browser and terminal runs coexist."""
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    for name, key in [('original.c', 'source'), ('before.ll', 'initial_ir'),
                      ('optimized.c', 'optimized_source'), ('optimized.ll', 'code'), ('optimized.s', 'optimized_assembly')]:
        if key in result:
            (root / name).write_text(result[key], encoding='utf-8')
    return root.resolve()
