"""Complete per-run C optimization reports for terminal and saved artifacts."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
import tempfile

from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from src.agent.autonomous import AutonomousOrchestrator
from src.llvm import IRParser, TACRenderer


COST_NOTE = ("Weighted cost = instructions + 3 × arithmetic operations + temporary values "
             "+ 10 × measured execution time in ms. This is a score, not money. "
             "Execution timings vary between runs. Guidance only suggests pass order; "
             "verified compiler passes produce the changes.")


def render_tac(ir: str) -> str:
    """Include all defined functions, rather than only main."""
    module = IRParser(ir).parse()
    return "\n\n".join(TACRenderer.render(module, fn.name)
                       for fn in module.functions if not fn.is_declaration)


def show_run(run, source: str, model_name=None, use_llm=False, *,
             report_path=None, show_output=None, console=None) -> Path:
    console = console or Console()
    model = (model_name or "Ollama default model") if use_llm else "Rule-based optimizer"
    before, after = asdict(run.initial_cost), asdict(run.final_cost)
    rows = [(label, before[key], after[key], before[key] - after[key])
            for key, label in [("weighted_cost", "Weighted cost"), ("instructions", "LLVM instructions"),
                               ("arithmetic", "Arithmetic operations"), ("temporaries", "Temporary values"),
                               ("runtime_ms", "Execution time (ms)")]]
    console.print(f"\nGuidance selected: {model}", markup=False)
    table = Table(title="Optimization effectiveness")
    for heading in ("Measure", "Before", "After", "Reduction"):
        table.add_column(heading)
    for label, initial, final, reduction in rows:
        table.add_row(label, f"{initial:.3f}", f"{final:.3f}", f"{reduction:.3f}")
    console.print(table)
    console.print(f"Cost reduction: {run.reduction_percent:.2f}% · Accepted optimizations: {run.accepted}")
    console.print(f"Verification: {'PASSED' if run.final_verification_passed else 'FAILED'} "
                  f"({run.verification_tests_passed}/{run.verification_tests_run} tests)")
    console.print(COST_NOTE)
    console.print("Guidance used: " + ", ".join(sorted({d.proposal_source for d in run.decisions}) or ["No proposals"]))
    console.print("Pipeline timings (seconds): " + json.dumps(run.timings))
    views = [("Original C source", source, "c"),
             ("TAC before optimization", render_tac(run.initial_ir), "text"),
             ("TAC after optimization", render_tac(run.final_ir), "text"),
             ("LLVM IR before optimization", run.initial_ir, "llvm"),
             ("Optimized code / LLVM IR after optimization", run.final_ir, "llvm")]
    console.print("Optimized code is executable LLVM IR; rewritten C source is not generated.")
    for title, code, language in views:
        console.print(f"\n{title}", style="bold cyan")
        console.print(Syntax(code, language, line_numbers=True, word_wrap=True))

    path = Path(report_path) if report_path else Path("reports/runs") / (
        Path(run.source_path).stem + "_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f")) / "REPORT.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    artifacts = path.parent / (path.stem + "_artifacts")
    artifacts.mkdir(exist_ok=True)
    for filename, content in [("original.c", source), ("before.ll", run.initial_ir),
                              ("optimized.ll", run.final_ir), ("before.tac", views[1][1]),
                              ("after.tac", views[2][1])]:
        (artifacts / filename).write_text(content, encoding="utf-8")
    summary = {"model": model, "initial_breakdown": before, "final_breakdown": after,
               "reduction_percent": run.reduction_percent, "accepted": run.accepted,
               "verification_passed": run.final_verification_passed,
               "tests_passed": run.verification_tests_passed, "tests_run": run.verification_tests_run,
               "timings": run.timings, "decisions": [asdict(d) for d in run.decisions]}
    (artifacts / "performance.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lines = ["# Optimization report", f"Guidance selected: {model}",
             f"Cost reduction: {run.reduction_percent:.2f}%", COST_NOTE,
             f"Verification: {summary['verification_passed']} ({summary['tests_passed']}/{summary['tests_run']})",
             "", "| Measure | Before | After | Reduction |", "|---|---:|---:|---:|"]
    lines += [f"| {label} | {initial:.3f} | {final:.3f} | {reduction:.3f} |"
              for label, initial, final, reduction in rows]
    for title, code, language in views:
        lines += ["", f"## {title}", f"`````{language}", code, "`````"]
    console.print(f"\nReport and compiler artifacts: {path.resolve()}", markup=False)
    if show_output is None:
        try:
            show_output = console.input("\nDisplay program output below the code? [y/N]: ").strip().lower() in {"y", "yes"}
        except EOFError:
            show_output = False
    if show_output:
        for title, output in [("Original program output", run.baseline_output),
                              ("Optimized program output", run.optimized_output)]:
            console.print(title, style="bold cyan")
            console.print(output or "(no output)", markup=False)
            lines += ["", f"## {title} · default verification run", "`````text", output or "(no output)", "`````"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    from src.experiment_history import save_experiment
    save_experiment(dict(summary, language="C", source=source, code=run.final_ir,
                         initial_ir=run.initial_ir, custom_optimizer=True,
                         initial_cost=before["weighted_cost"], final_cost=after["weighted_cost"],
                         baseline_output=run.baseline_output, optimized_output=run.optimized_output),
                    interface="Terminal", source_name=Path(run.source_path).name, report_path=path)
    return path


def run_file(source_path, *, model_name=None, use_llm=False, report_path=None,
             show_output=None, benchmark=False, iterations=15, chart=None, diff=False):
    """Use the same verified optimizer as Streamlit for file-based CLI runs."""
    run = AutonomousOrchestrator(use_llm=use_llm, model_name=model_name).optimize_file(str(source_path))
    report = show_run(run, Path(source_path).read_text(encoding="utf-8"), model_name, use_llm,
                      report_path=report_path, show_output=show_output)
    if diff:
        from src.cli.interface import CompilerCLI
        CompilerCLI().print_ir_diff(run.initial_ir, run.final_ir)
    if benchmark:
        from src.llvm import ClangRunner
        from src.benchmarking import Benchmarker, BenchmarkVisualizer
        from src.cli.interface import CompilerCLI
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = ClangRunner()
            binaries = []
            for name, ir in [("before", run.initial_ir), ("after", run.final_ir)]:
                ir_path = root / f"{name}.ll"
                ir_path.write_text(ir, encoding="utf-8")
                binary = root / name
                runner.compile_ir_to_binary(str(ir_path), str(binary))
                binaries.append(str(binary))
            references = []
            for level in ("-O1", "-O2"):
                binary = root / level
                runner.compile_c_to_binary(str(source_path), str(binary), opt_level=level)
                references.append(str(binary))
            result = Benchmarker(iterations=iterations).run_benchmark(
                *binaries, *references, base_inst_count=run.initial_cost.instructions,
                opt_inst_count=run.final_cost.instructions)
            CompilerCLI().print_benchmark(result)
            BenchmarkVisualizer.generate_chart(result, Path(source_path).stem,
                                                chart or str(report.parent / "benchmark.png"))
    return run
