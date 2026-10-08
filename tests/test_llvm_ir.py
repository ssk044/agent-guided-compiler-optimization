"""
Unit tests for ClangRunner, IRParser, and IREmitter.
"""
import os
import tempfile
from src.llvm import ClangRunner, IRParser, IREmitter


def test_llvm_ir_roundtrip():
    code = """
    #include <stdio.h>
    int mult(int a, int b) {
        return a * b;
    }
    int main() {
        printf("res: %d\\n", mult(6, 7));
        return 0;
    }
    """
    runner = ClangRunner()
    with tempfile.TemporaryDirectory() as td:
        c_file = os.path.join(td, "test.c")
        ll_file = os.path.join(td, "test.ll")
        re_ll_file = os.path.join(td, "re_test.ll")
        bin_file = os.path.join(td, "test.bin")

        with open(c_file, "w") as f:
            f.write(code)

        runner.compile_to_ir(c_file, ll_file)
        with open(ll_file) as f:
            text = f.read()

        module = IRParser(text).parse()
        assert len(module.functions) >= 2

        IREmitter.write_to_file(module, re_ll_file)
        runner.compile_ir_to_binary(re_ll_file, bin_file)

        res = runner.execute_binary(bin_file)
        assert res.returncode == 0
        assert "res: 42" in res.stdout
