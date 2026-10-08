"""
LLVM IR Emitter that renders and serializes IRModule to valid textual LLVM IR (.ll).
"""
import os
from src.llvm.ir_nodes import IRModule


class IREmitter:
    @staticmethod
    def emit(module: IRModule) -> str:
        """Serializes IRModule to textual LLVM IR format."""
        return module.render()

    @staticmethod
    def write_to_file(module: IRModule, output_path: str) -> None:
        """Writes the LLVM IR to a file on disk."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        content = module.render()
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
