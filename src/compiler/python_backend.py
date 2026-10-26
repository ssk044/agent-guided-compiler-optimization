"""CPython bytecode compilation adapter for the Streamlit workbench.

Python source is compiled but never executed by this module. CPython's own
compiler performs its standard optimizations at the requested optimization
level; this is separate from the project's custom LLVM optimization passes.
"""
from __future__ import annotations

import dis
import importlib.util
import io
import marshal
import struct
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class PythonCompilation:
    bytecode_listing: str
    pyc_bytes: bytes
    elapsed_seconds: float
    compile_seconds: float
    optimization_level: int
    code_object: Any


def compile_python(source: str, optimization_level: int = 0, filename: str = "<workbench>") -> PythonCompilation:
    """Compile Python source into CPython bytecode and a version-specific .pyc."""
    if optimization_level not in (0, 1, 2):
        raise ValueError("Python optimization level must be 0, 1, or 2.")

    started = time.perf_counter()
    compile_started = time.perf_counter()
    code = compile(source, filename, "exec", optimize=optimization_level)
    compile_seconds = time.perf_counter() - compile_started

    listing = io.StringIO()
    dis.dis(code, file=listing, depth=None)

    # PEP 552 checked-hash pyc header: magic, flags, source hash, marshalled code.
    flags = 0b11
    header = importlib.util.MAGIC_NUMBER + struct.pack("<I", flags)
    pyc_bytes = header + importlib.util.source_hash(source.encode("utf-8")) + marshal.dumps(code)
    elapsed = time.perf_counter() - started
    return PythonCompilation(
        bytecode_listing=listing.getvalue(),
        pyc_bytes=pyc_bytes,
        elapsed_seconds=elapsed,
        compile_seconds=compile_seconds,
        optimization_level=optimization_level,
        code_object=code,
    )
