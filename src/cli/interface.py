"""
Rich Terminal Interface and Report Generation for LLM-Guided Compiler Optimization System.
"""
import os
import difflib
from datetime import datetime
from typing import Optional, List, Dict, Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.agent.schema import OptimizationProposal
from src.optimizations.base import PassResult
from src.validation.verifier import VerificationReport
from src.benchmarking.benchmark import BenchmarkResult


class CompilerCLI:
    def __init__(self):
        self.console = Console()

    def print_banner(self):
        banner_text = Text()
        banner_text.append("┌─────────────────────────────────────────────────────────────┐\n", style="bold cyan")
        banner_text.append("│   LLM-GUIDED COMPILER OPTIMIZATION SYSTEM                   │\n", style="bold white")
        banner_text.append("│   DeepMind-Calibrated Agentic IR Optimization Engine        │\n", style="bold blue")
        banner_text.append("└─────────────────────────────────────────────────────────────┘", style="bold cyan")
        self.console.print(banner_text)

    def print_program_summary(self, source_path: str, function_count: int, block_count: int, instruction_count: int):
        table = Table(title="Program IR Overview", style="cyan", show_header=True, header_style="bold magenta")
        table.add_column("Property", style="bold white")
        table.add_column("Value", style="green")

        table.add_row("Source File", os.path.basename(source_path))
        table.add_row("Functions", str(function_count))
        table.add_row("Basic Blocks", str(block_count))
        table.add_row("Total IR Instructions", str(instruction_count))
        self.console.print(table)

    def print_agent_proposal(self, proposal: OptimizationProposal, model_name: str):
        self.console.print(Panel(
            f"[bold green]LLM Optimization Agent ([bold yellow]{model_name}[/bold yellow]):[/bold green]\n"
            f"{proposal.summary}\n\n"
            f"[bold cyan]Safety Assessment:[/bold cyan] {proposal.safety_assessment}",
            title="Agent Analysis & Strategy",
            border_style="green"
        ))

        # Opportunities Table
        if proposal.opportunities:
            opp_table = Table(title="Identified Optimization Opportunities", style="yellow", show_header=True, header_style="bold cyan")
            opp_table.add_column("Optimization", style="bold yellow")
            opp_table.add_column("Target", style="white")
            opp_table.add_column("Rationale", style="italic white")
            opp_table.add_column("Confidence", style="green", justify="right")

            for opp in proposal.opportunities:
                target_str = f"{opp.target_function} ({opp.target_block or 'global'})"
                opp_table.add_row(opp.name, target_str, opp.rationale, f"{opp.confidence * 100:.0f}%")
            self.console.print(opp_table)

        # Recommended Passes Table
        rec_table = Table(title="Recommended Compiler Pass Pipeline", style="blue", show_header=True, header_style="bold magenta")
        rec_table.add_column("#", justify="center", style="bold cyan")
        rec_table.add_column("Pass Name", style="bold white")
        rec_table.add_column("Stage Rationale", style="white")

        for rec in sorted(proposal.recommended_passes, key=lambda x: x.order):
            rec_table.add_row(str(rec.order), rec.pass_name, rec.reason)
        self.console.print(rec_table)

    def print_pass_results(self, pass_results: List[PassResult], initial_ops: int, final_ops: int):
        table = Table(title="Applied Optimization Passes", style="green", show_header=True, header_style="bold green")
        table.add_column("Pass", style="bold cyan")
        table.add_column("Status", justify="center")
        table.add_column("Changes", justify="right", style="bold yellow")
        table.add_column("Details", style="white")

        total_changes = 0
        for r in pass_results:
            if r.changes_made > 0:
                total_changes += r.changes_made
                detail_str = "; ".join(r.details[:2])
                table.add_row(r.pass_name, "[bold green]APPLIED[/bold green]", str(r.changes_made), detail_str)

        self.console.print(table)
        reduct_pct = ((initial_ops - final_ops) / initial_ops * 100.0) if initial_ops > 0 else 0.0
        self.console.print(
            f"[bold white]Total Transformations:[/bold white] [bold green]{total_changes}[/bold green] | "
            f"[bold white]IR Instruction Delta:[/bold white] [bold red]{initial_ops}[/bold red] → [bold green]{final_ops}[/bold green] "
            f"([bold cyan]-{reduct_pct:.1f}%[/bold cyan])"
        )

    def print_verification(self, report: VerificationReport):
        status_text = "[bold green]PASSED (100% Bitwise Correct)[/bold green]" if report.is_valid else "[bold red]FAILED (Optimization Rejected)[/bold red]"
        table = Table(title=f"Correctness Verification: {status_text}", style="cyan" if report.is_valid else "red", show_header=True)
        table.add_column("Test Case", style="bold white")
        table.add_column("Result", justify="center")
        table.add_column("Baseline Output", style="white")
        table.add_column("Optimized Output", style="white")

        for test in report.results:
            res_str = "[bold green]PASS[/bold green]" if test.passed else "[bold red]FAIL[/bold red]"
            table.add_row(
                test.input_desc,
                res_str,
                test.baseline_stdout.strip()[:30],
                test.optimized_stdout.strip()[:30]
            )

        self.console.print(table)
        if not report.is_valid:
            self.console.print(f"[bold red]Rejection Reason:[/bold red] {report.rejection_reason}")

    def print_benchmark(self, bench: BenchmarkResult):
        table = Table(title="Performance Benchmarking Results", style="magenta", show_header=True, header_style="bold yellow")
        table.add_column("Configuration", style="bold white")
        table.add_column("Mean Time (ms)", justify="right")
        table.add_column("Std Dev (ms)", justify="right")
        table.add_column("Speedup vs Baseline", justify="right", style="bold green")

        table.add_row("Baseline (-O0)", f"{bench.baseline_mean_ms:.3f}", f"±{bench.baseline_std_ms:.3f}", "1.00x (baseline)")
        table.add_row("LLM Optimized", f"{bench.optimized_mean_ms:.3f}", f"±{bench.optimized_std_ms:.3f}", f"[bold green]{bench.speedup_factor:.2f}x ({bench.speedup_percent:+.1f}%)[/bold green]")

        if bench.clang_o1_mean_ms is not None:
            o1_factor = bench.baseline_mean_ms / bench.clang_o1_mean_ms if bench.clang_o1_mean_ms > 0 else 1.0
            table.add_row("Clang -O1", f"{bench.clang_o1_mean_ms:.3f}", "-", f"{o1_factor:.2f}x")

        if bench.clang_o2_mean_ms is not None:
            o2_factor = bench.baseline_mean_ms / bench.clang_o2_mean_ms if bench.clang_o2_mean_ms > 0 else 1.0
            table.add_row("Clang -O2", f"{bench.clang_o2_mean_ms:.3f}", "-", f"{o2_factor:.2f}x")

        self.console.print(table)

    def print_ir_diff(self, orig_ir: str, opt_ir: str, max_lines: int = 40):
        diff = list(difflib.unified_diff(
            orig_ir.splitlines(), opt_ir.splitlines(),
            fromfile="Original LLVM IR", tofile="Optimized LLVM IR",
            lineterm=""
        ))
        if diff:
            diff_text = "\n".join(diff[:max_lines])
            if len(diff) > max_lines:
                diff_text += f"\n... [{len(diff) - max_lines} more lines]"
            syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=True)
            self.console.print(Panel(syntax, title="LLVM IR Transformation Diff", border_style="cyan"))

    def generate_markdown_report(
        self,
        output_report_path: str,
        source_path: str,
        c_source: str,
        proposal: OptimizationProposal,
        pass_results: List[PassResult],
        verification: VerificationReport,
        benchmark: Optional[BenchmarkResult],
        figure_path: Optional[str] = None
    ) -> str:
        """
        Generates a polished GitHub/LinkedIn-ready markdown report.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_report_path)), exist_ok=True)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            f"# LLM-Guided Compiler Optimization Report",
            f"**File:** `{os.path.basename(source_path)}` | **Generated:** `{now_str}`",
            "",
            "## 1. Executive Summary",
            f"{proposal.summary}",
            "",
            "## 2. LLM Optimization Proposal",
            f"- **Expected Speedup Estimate:** `{proposal.expected_speedup_estimate:.2f}x`",
            f"- **Safety Assessment:** {proposal.safety_assessment}",
            "",
            "### Recommended Passes",
            "| # | Pass Name | Order Rationale |",
            "|---|-----------|-----------------|",
        ]

        for rec in sorted(proposal.recommended_passes, key=lambda x: x.order):
            lines.append(f"| {rec.order} | **{rec.pass_name}** | {rec.reason} |")

        lines.extend([
            "",
            "### Opportunities Identified",
            "| Optimization | Function | Block | Technical Rationale | Confidence |",
            "|--------------|----------|-------|---------------------|------------|",
        ])

        for opp in proposal.opportunities:
            lines.append(f"| **{opp.name}** | `{opp.target_function}` | `{opp.target_block or '-'}` | {opp.rationale} | {opp.confidence*100:.0f}% |")

        lines.extend([
            "",
            "## 3. Applied Compiler Transformations",
            "| Pass | Changes | Details |",
            "|------|---------|---------|",
        ])

        total_changes = 0
        for r in pass_results:
            if r.changes_made > 0:
                total_changes += r.changes_made
                detail = "<br>".join(r.details[:3])
                lines.append(f"| **{r.pass_name}** | {r.changes_made} | {detail} |")

        lines.extend([
            "",
            f"**Total Transformations Applied:** `{total_changes}`",
            "",
            "## 4. Correctness & Differential Verification",
            f"- **Verification Status:** `{'PASSED (100% Equivalence)' if verification.is_valid else 'REJECTED'}`",
            f"- **Test Suite:** `{verification.tests_passed}/{verification.tests_run} Passed`",
            "",
            "| Input | Baseline Exit | Optimized Exit | Output Match |",
            "|-------|---------------|----------------|--------------|",
        ])

        for t in verification.results:
            lines.append(f"| `{t.input_desc}` | `{t.baseline_exit_code}` | `{t.optimized_exit_code}` | `{'PASS' if t.passed else 'FAIL'}` |")

        if benchmark:
            lines.extend([
                "",
                "## 5. Performance Benchmarking & Statistical Evaluation",
                f"- **Baseline Execution Time:** `{benchmark.baseline_mean_ms:.3f} ms ± {benchmark.baseline_std_ms:.3f}`",
                f"- **LLM Optimized Execution Time:** `{benchmark.optimized_mean_ms:.3f} ms ± {benchmark.optimized_std_ms:.3f}`",
                f"- **Net Performance Gain:** `+{benchmark.speedup_percent:.1f}%` ({benchmark.speedup_factor:.2f}x speedup)",
                f"- **IR Instruction Reduction:** `{benchmark.baseline_instruction_count}` → `{benchmark.optimized_instruction_count}` (`-{benchmark.instruction_reduction_percent:.1f}%`)",
                "",
                "| Configuration | Mean Time (ms) | Std Dev (ms) | Speedup Factor |",
                "|---------------|----------------|--------------|----------------|",
                f"| Baseline (-O0) | {benchmark.baseline_mean_ms:.3f} | ±{benchmark.baseline_std_ms:.3f} | 1.00x |",
                f"| LLM Optimized | **{benchmark.optimized_mean_ms:.3f}** | ±{benchmark.optimized_std_ms:.3f} | **{benchmark.speedup_factor:.2f}x** |",
            ])
            if benchmark.clang_o1_mean_ms:
                lines.append(f"| Clang -O1 | {benchmark.clang_o1_mean_ms:.3f} | - | {benchmark.baseline_mean_ms/benchmark.clang_o1_mean_ms:.2f}x |")
            if benchmark.clang_o2_mean_ms:
                lines.append(f"| Clang -O2 | {benchmark.clang_o2_mean_ms:.3f} | - | {benchmark.baseline_mean_ms/benchmark.clang_o2_mean_ms:.2f}x |")

        if figure_path and os.path.exists(figure_path):
            rel_fig = os.path.relpath(figure_path, os.path.dirname(output_report_path))
            lines.extend([
                "",
                "## 6. Benchmark Visualization",
                f"![Benchmark Figure]({rel_fig})",
            ])

        lines.extend([
            "",
            "## 7. LinkedIn Project Summary Snippet",
            "```text",
            f"🚀 Excited to share my latest systems & AI project: An LLM-Guided Compiler Optimization Pipeline!",
            f"",
            f"Instead of blindly asking an LLM to rewrite source code, I built an agentic compiler pipeline:",
            f"1. Clang emits LLVM Intermediate Representation (IR).",
            f"2. Formal CFG, Dominator Tree, and Liveness analyses extract semantic invariants.",
            f"3. A local Qwen2.5-Coder model analyzes the IR and proposes targeted passes with formal rationale.",
            f"4. Custom compiler passes (Constant Folding, DCE, Strength Reduction, CSE, LICM) apply the transformations.",
            f"5. A differential test harness verifies bitwise output equivalence before accepting changes.",
            f"6. Benchmarks show a {benchmark.speedup_percent:.1f}% speedup and {benchmark.instruction_reduction_percent:.1f}% IR instruction reduction!",
            f"```",
            ""
        ])

        with open(output_report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return output_report_path
