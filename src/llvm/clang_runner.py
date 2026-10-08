"""
Clang/LLVM runner for IR generation, compilation, pass execution, and native execution.
"""
import os
import time
import subprocess
from dataclasses import dataclass
from typing import List, Optional


class ClangError(Exception):
    def __init__(self, message: str, stderr: str = "", command: Optional[List[str]] = None):
        super().__init__(f"{message}\nCommand: {' '.join(command or [])}\nError: {stderr}")
        self.stderr = stderr
        self.command = command


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    returncode: int
    elapsed_time_seconds: float
    timed_out: bool = False


class ClangRunner:
    def __init__(self, clang_bin: str = "clang"):
        self.clang_bin = clang_bin

    def compile_to_ir(
        self,
        c_source_path: str,
        ir_output_path: str,
        opt_level: str = "-O0",
        disable_optnone: bool = True
    ) -> str:
        """
        Compiles C/C++ source code to LLVM IR (.ll).
        Uses -Xclang -disable-O0-optnone to ensure functions can be optimized later.
        """
        cmd = [self.clang_bin, "-S", "-emit-llvm", opt_level, "-fno-discard-value-names"]
        if opt_level == "-O0" and disable_optnone:
            cmd.extend(["-Xclang", "-disable-O0-optnone"])
        cmd.extend([c_source_path, "-o", ir_output_path])

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise ClangError(f"Failed to generate LLVM IR for {c_source_path}", res.stderr, cmd)
        return ir_output_path

    def compile_ir_to_binary(
        self,
        ir_path: str,
        binary_output_path: str,
        opt_flags: Optional[List[str]] = None
    ) -> str:
        """
        Compiles textual LLVM IR (.ll) to a native executable binary.
        """
        cmd = [self.clang_bin]
        if opt_flags:
            cmd.extend(opt_flags)
        cmd.extend([ir_path, "-o", binary_output_path])

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise ClangError(f"Failed to compile LLVM IR to binary: {ir_path}", res.stderr, cmd)
        return binary_output_path

    def compile_ir_to_assembly(self, ir_path: str, assembly_output_path: str) -> str:
        """Lowers LLVM IR to target assembly for the code-generation demonstration."""
        cmd = [self.clang_bin, "-S", ir_path, "-o", assembly_output_path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise ClangError(f"Failed to compile LLVM IR to assembly: {ir_path}", res.stderr, cmd)
        return assembly_output_path

    def compile_c_to_binary(
        self,
        c_source_path: str,
        binary_output_path: str,
        opt_level: str = "-O0"
    ) -> str:
        """
        Directly compiles C source to native binary with given optimization level.
        """
        cmd = [self.clang_bin, opt_level, c_source_path, "-o", binary_output_path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise ClangError(f"Failed to compile C source to binary: {c_source_path}", res.stderr, cmd)
        return binary_output_path

    def optimize_ir(
        self,
        ir_input_path: str,
        ir_output_path: str,
        opt_level: str = "-O2"
    ) -> str:
        """
        Runs Clang optimization pipeline directly on LLVM IR.
        """
        cmd = [self.clang_bin, opt_level, "-S", "-emit-llvm", ir_input_path, "-o", ir_output_path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise ClangError(f"Failed to optimize LLVM IR: {ir_input_path}", res.stderr, cmd)
        return ir_output_path

    def execute_binary(
        self,
        binary_path: str,
        args: Optional[List[str]] = None,
        stdin_input: Optional[str] = None,
        timeout: float = 10.0
    ) -> ExecutionResult:
        """
        Executes native binary, measures execution time, and captures stdout/stderr.
        """
        cmd = [os.path.abspath(binary_path)]
        if args:
            cmd.extend(args)

        t_start = time.perf_counter()
        try:
            res = subprocess.run(
                cmd,
                input=stdin_input,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            elapsed = time.perf_counter() - t_start
            return ExecutionResult(
                stdout=res.stdout,
                stderr=res.stderr,
                returncode=res.returncode,
                elapsed_time_seconds=elapsed,
                timed_out=False
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                stdout="",
                stderr=f"Execution timed out after {timeout} seconds",
                returncode=-1,
                elapsed_time_seconds=timeout,
                timed_out=True
            )
        except Exception as e:
            return ExecutionResult(
                stdout="",
                stderr=str(e),
                returncode=-1,
                elapsed_time_seconds=0.0,
                timed_out=False
            )
