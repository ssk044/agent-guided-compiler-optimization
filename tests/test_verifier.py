"""
Unit tests for CorrectnessVerifier.
"""
import os
import tempfile
from src.llvm import ClangRunner
from src.validation import CorrectnessVerifier


def test_verifier_identical_binaries():
    code = """
    #include <stdio.h>
    int main(int argc, char* argv[]) {
        printf("Hello World %d\\n", argc);
        return 0;
    }
    """
    runner = ClangRunner()
    verifier = CorrectnessVerifier(runner=runner)

    with tempfile.TemporaryDirectory() as td:
        c1 = os.path.join(td, "b1.c")
        c2 = os.path.join(td, "b2.c")
        bin1 = os.path.join(td, "bin1")
        bin2 = os.path.join(td, "bin2")

        with open(c1, "w") as f: f.write(code)
        with open(c2, "w") as f: f.write(code)

        runner.compile_c_to_binary(c1, bin1)
        runner.compile_c_to_binary(c2, bin2)

        report = verifier.verify(bin1, bin2)
        assert report.is_valid is True
        assert report.tests_passed == report.tests_run


def test_verifier_detects_output_mismatch():
    code1 = '#include <stdio.h>\nint main() { printf("answer: 42\\n"); return 0; }'
    code2 = '#include <stdio.h>\nint main() { printf("answer: 99\\n"); return 0; }'

    runner = ClangRunner()
    verifier = CorrectnessVerifier(runner=runner)

    with tempfile.TemporaryDirectory() as td:
        bin1 = os.path.join(td, "bin1")
        bin2 = os.path.join(td, "bin2")
        c1 = os.path.join(td, "b1.c")
        c2 = os.path.join(td, "b2.c")
        with open(c1, "w") as f: f.write(code1)
        with open(c2, "w") as f: f.write(code2)

        runner.compile_c_to_binary(c1, bin1)
        runner.compile_c_to_binary(c2, bin2)

        report = verifier.verify(bin1, bin2)
        assert report.is_valid is False
        assert "mismatch" in report.rejection_reason.lower()
