"""Terminal UI for pasting a C program and watching the autonomous agent work."""
from __future__ import annotations
import os
import tempfile
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from src.agent.autonomous import AutonomousOrchestrator, write_decision_log
from src.llvm import IRParser, IREmitter, TACRenderer
from src.llvm.clang_runner import ClangError, ClangRunner


def run_interactive(model_name: str | None = None, use_llm: bool = False) -> None:
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
    default = "Y/n" if use_llm else "y/N"
    answer = input(f"Use Qwen/Ollama to guide optimization proposals? [{default}]: ").strip().lower()
    if answer:
        use_llm = answer in {"y", "yes"}
    academic_answer = input("Show TAC and target-assembly learning views? [y/N]: ").strip().lower()
    show_academic_views = academic_answer in {"y", "yes"}
    with tempfile.TemporaryDirectory(prefix="interactive_agent_") as directory:
        path = os.path.join(directory, "pasted_program.c")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(source + "\n")
        mode = "Qwen-guided proposals" if use_llm else "rule-based proposals"
        console.print(f"[cyan]Mode: {mode}. Compiling, analyzing, verifying, and evaluating…[/cyan]")
        try:
            run = AutonomousOrchestrator(use_llm=use_llm, model_name=model_name).optimize_file(path)
        except ClangError as error:
            console.print("[bold red]Compilation failed.[/bold red]")
            console.print(error.stderr.strip())
            console.print("[yellow]Correct the C code and run option 1 again.[/yellow]")
            return
        table = Table(title="Optimization Results")
        for column in ("Step", "Pass", "Verified", "Cost", "Outcome", "Reason"):
            table.add_column(column)
        meaningful = [d for d in run.decisions if d.decision != "skipped"]
        skipped = len(run.decisions) - len(meaningful)
        for decision in meaningful:
            table.add_row(str(decision.iteration), decision.pass_name, "PASS" if decision.verified else "FAIL",
                          f"{decision.cost_before:.2f} → {decision.cost_after:.2f}",
                          decision.decision.upper(), decision.reason[:72])
        console.print(table)
        console.print(f"[dim]{skipped} pass checks skipped because no opportunity remained.[/dim]")
        verdict = "PASS" if run.final_verification_passed else "FAIL"
        color = "green" if run.final_verification_passed else "red"
        console.print("[bold cyan]Program Output Verification:[/bold cyan]")
        console.print(f"  Original output:  {run.baseline_output.strip() or '(no output)'}")
        console.print(f"  Optimized output: {run.optimized_output.strip() or '(no output)'}")
        console.print(f"  Tests matched: {run.verification_tests_passed}/{run.verification_tests_run}")
        console.print(f"[bold {color}]Final verdict: {verdict}[/bold {color}] | Cost reduction: {run.reduction_percent:.1f}% | Accepted changes: {run.accepted}")
        console.print("[bold cyan]Optimized LLVM IR (main function):[/bold cyan]")
        console.print(Syntax(_function_excerpt(run.final_ir), "llvm", theme="monokai", line_numbers=False))
        if show_academic_views:
            _show_academic_views(console, run.initial_ir, run.final_ir, directory)
        output = os.path.abspath("reports/interactive_decision_log.json")
        write_decision_log(run, output)
        console.print(f"Decision log saved to [cyan]{output}[/cyan]")


def _function_excerpt(ir_text: str) -> str:
    """Keep presentation output focused; metadata remains in the saved IR/log."""
    lines = ir_text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith("define") and "@main" in line), None)
    if start is None:
        return ir_text
    end = next((i for i in range(start + 1, len(lines)) if lines[i] == "}"), len(lines) - 1)
    return "\n".join(lines[start:end + 1])


def _show_academic_views(console: Console, initial_ir: str, final_ir: str, directory: str) -> None:
    """Optional concise artifacts for TAC and target-code syllabus topics."""
    before_tac = TACRenderer.render(IRParser(initial_ir).parse())
    after_tac = TACRenderer.render(IRParser(final_ir).parse())
    console.print("[bold cyan]TAC-style intermediate code (before optimization):[/bold cyan]")
    console.print(Syntax(_truncate(before_tac), "text", theme="monokai"))
    console.print("[bold cyan]TAC-style intermediate code (after optimization):[/bold cyan]")
    console.print(Syntax(_truncate(after_tac), "text", theme="monokai"))
    ir_path = os.path.join(directory, "optimized.ll")
    asm_path = os.path.join(directory, "optimized.s")
    try:
        with open(ir_path, "w", encoding="utf-8") as handle:
            handle.write(final_ir)
        ClangRunner().compile_ir_to_assembly(ir_path, asm_path)
        assembly = open(asm_path, encoding="utf-8").read()
        console.print("[bold cyan]Target assembly excerpt:[/bold cyan]")
        console.print(Syntax(_truncate(assembly, 24), "asm", theme="monokai"))
    except ClangError as error:
        console.print(f"[yellow]Assembly view unavailable: {error.stderr.strip()}[/yellow]")


def _truncate(text: str, limit: int = 28) -> str:
    lines = text.splitlines()
    suffix = "\n…" if len(lines) > limit else ""
    return "\n".join(lines[:limit]) + suffix
