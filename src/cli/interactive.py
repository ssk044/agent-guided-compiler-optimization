"""Terminal UI for pasting a C program and watching the autonomous agent work."""
from __future__ import annotations
import os
import tempfile
from rich.console import Console
from rich.syntax import Syntax
from src.agent.autonomous import AutonomousOrchestrator, write_decision_log
from src.llvm.clang_runner import ClangError
from src.cli.run_report import show_run


def run_interactive(model_name: str | None = None, use_llm: bool = False, *, show_output: bool | None = None, backend: str = "auto", native_level: str = "-O2") -> None:
    console = Console()
    console.print("[bold cyan]Paste a complete C program. Type END on a line by itself to run it.[/bold cyan]")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "END":
            break
        lines.append(line)
    source = "\n".join(lines).strip()
    # Permit code copied directly from Markdown/chat responses.
    if source.startswith("```"):
        source_lines = source.splitlines()
        source_lines = source_lines[1:]
        if source_lines and source_lines[-1].strip().startswith("```"):
            source_lines = source_lines[:-1]
        source = "\n".join(source_lines).strip()
    if not source:
        console.print("[red]No source received.[/red]")
        return
    proceed = input("Compile, optimize, and show the optimized code? [Y/n]: ").strip().lower()
    if proceed in {"n", "no"}:
        console.print("[dim]Optimization cancelled.[/dim]")
        return
    default = "Y/n" if use_llm else "y/N"
    answer = input(f"Use Qwen/Ollama to guide optimization proposals? [{default}]: ").strip().lower()
    if answer:
        use_llm = answer in {"y", "yes"}
    with tempfile.TemporaryDirectory(prefix="interactive_agent_") as directory:
        path = os.path.join(directory, "pasted_program.c")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(source + "\n")
        mode = "Qwen-guided proposals" if use_llm else "rule-based proposals"
        console.print(f"[cyan]Mode: {mode}. Compiling, analyzing, verifying, and evaluating…[/cyan]")
        if backend == "clang":
            from src.cli.native_report import compile_native_file
            compile_native_file(path, level=native_level, show_output=show_output)
            return
        try:
            run = AutonomousOrchestrator(use_llm=use_llm, model_name=model_name).optimize_file(path)
        except Exception as error:
            if backend == "custom":
                console.print("Custom optimization failed:", style="red")
                console.print(str(error), markup=False)
                return
            console.print("Custom pipeline could not process this program; trying native Clang.")
            from src.cli.native_report import compile_native_file
            try:
                compile_native_file(path, level=native_level, show_output=show_output)
            except (ClangError, OSError, ValueError) as native_error:
                console.print(str(native_error), markup=False, style="red")
            return
        show_run(run, source, model_name, use_llm, show_output=show_output, console=console)
        output = os.path.abspath("reports/interactive_decision_log.json")
        write_decision_log(run, output)
