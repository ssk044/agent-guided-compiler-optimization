#!/usr/bin/env python3
"""
LLM-Guided Compiler Optimization System - Main CLI Entrypoint.
Orchestrates Lexer, Parser, AST, Semantic, LLVM IR, Analysis, LLM Agent,
Optimizations, Correctness Verification, and Performance Benchmarking.
"""
import sys
import os
import argparse
import tempfile
from typing import Optional

from src.lexer import Lexer
from src.parser import Parser
from src.ast import ASTPrinter
from src.semantic import SemanticAnalyzer
from src.llvm import ClangRunner, IRParser, IREmitter
from src.llvm.clang_runner import ClangError
from src.analysis import ControlFlowGraph, DominatorAnalysis, LoopAnalysis, DefUseAnalysis
from src.agent import OptimizationAgent
from src.optimizations import PassManager
from src.validation import CorrectnessVerifier
from src.benchmarking import Benchmarker, BenchmarkVisualizer
from src.benchmarking import DatasetExperiment
from src.dataset import DatasetGenerator
from src.cli import CompilerCLI
from src.cli.interactive import run_interactive
from src.cli.run_report import run_file
from rich.syntax import Syntax


def start_menu(args) -> None:
    """Presentation entry point: choose custom C input or the benchmark dataset."""
    print("\n=== Automated LLM/Agent-Guided Compiler Optimizer ===")
    print("1. Paste my own C program")
    print("2. Run prepared dataset demo (10 programs)")
    print("3. Run full prepared dataset (500 programs)")
    choice = input("Choose 1, 2, or 3: ").strip()
    if choice == "1":
        run_interactive(args.model, args.llm, show_output=args.show_output, backend=args.backend, native_level=args.native_level)
        return
    if choice in {"2", "3"}:
        programs = DatasetGenerator(args.dataset_dir).generate()
        limit = 10 if choice == "2" else None
        summary = DatasetExperiment(args.dataset_report_dir, use_llm=args.llm,
                                    model_name=args.model).run(programs, limit)
        print(f"\nComplete: {summary['programs']} program(s), {summary['accepted']} accepted optimization(s).")
        print(f"Open: {os.path.join(args.dataset_report_dir, 'REPORT.md')}")
        return
    print("Invalid selection. Please run the command again and select 1, 2, or 3.")


def main():
    parser = argparse.ArgumentParser(
        description="LLM-Guided Compiler Optimization System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python main.py examples/01_constant_calc.c
  python main.py examples/02_matrix_multiply.c --benchmark --diff
  python main.py examples/03_redundant_compute.c --analyze
  python main.py examples/04_loop_invariants.c --model qwen2.5-coder:3b
"""
    )
    parser.add_argument("source_file", nargs="?", help="Path to C/C++ source file")
    parser.add_argument("--analyze", action="store_true", help="Run lexical, AST, semantic, and CFG analysis")
    parser.add_argument("--emit-ir", action="store_true", help="Emit unoptimized LLVM IR to stdout/file")
    parser.add_argument("--optimize", action="store_true", help="Run LLM optimization agent and apply passes")
    parser.add_argument("--validate", action="store_true", help="Run correctness verification tests")
    parser.add_argument("--benchmark", action="store_true", help="Run performance benchmarks (baseline vs optimized vs -O1/-O2)")
    parser.add_argument("--diff", action="store_true", help="Display visual diff of baseline vs optimized LLVM IR")
    parser.add_argument("--model", type=str, default=None, help="Local Ollama model name (default: qwen2.5-coder:3b)")
    parser.add_argument("--report", type=str, default=None, help="Output path for Markdown optimization report")
    parser.add_argument("--chart", type=str, default=None, help="Output path for benchmark PNG chart")
    parser.add_argument("--iterations", type=int, default=15, help="Number of benchmark timing iterations (default: 15)")
    parser.add_argument("--generate-dataset", action="store_true", help="Generate the reproducible 500-program C dataset")
    parser.add_argument("--run-dataset", action="store_true", help="Generate and run the autonomous dataset experiment")
    parser.add_argument("--dataset-dir", default="dataset/programs", help="Dataset location (default: dataset/programs)")
    parser.add_argument("--dataset-limit", type=int, default=None, help="Process only the first N generated programs (quick demo)")
    parser.add_argument("--dataset-report-dir", default="reports/dataset", help="Dataset report output directory")
    parser.add_argument("--interactive", action="store_true", help="Paste C code and view the full agent decision log")
    parser.add_argument("--llm", action="store_true", help="Use local Ollama/Qwen to order proposals (verification remains mandatory)")

    parser.add_argument("--backend", choices=["auto", "custom", "clang"], default="auto", help="C backend: native Clang handles complex constructs without the educational IR parser")
    parser.add_argument("--native-level", choices=["-O1", "-O2", "-O3", "-Os"], default="-O2")
    parser.add_argument("--python-opt", type=int, choices=[0, 1, 2], default=0, help="Python bytecode optimization; 1 removes asserts, 2 also removes docstrings")
    parser.add_argument("--stdin-file", help="Text file to supply as standard input for explicit native/Python execution")
    parser.add_argument("--timeout", type=int, choices=range(1, 61), default=5, metavar="1..60")
    output_options = parser.add_mutually_exclusive_group()
    output_options.add_argument("--show-output", dest="show_output", action="store_true", help="Display original and optimized program output below the code")
    output_options.add_argument("--no-output", dest="show_output", action="store_false", help="Skip output display (for non-interactive runs)")
    parser.set_defaults(show_output=None)
    parser.add_argument("--history", action="store_true", help="Browse saved experiments without compiling")
    parser.add_argument("--no-history-prompt", action="store_true", help="Skip the history question after a run")
    args = parser.parse_args()
    from src.experiment_history import browse_terminal
    if args.history:
        browse_terminal(prompt=False)
        return


    if args.interactive:
        run_interactive(args.model, args.llm, show_output=args.show_output, backend=args.backend, native_level=args.native_level)
        if not args.no_history_prompt:
            browse_terminal()
        return

    if args.generate_dataset or args.run_dataset:
        programs = DatasetGenerator(args.dataset_dir).generate()
        print(f"Generated {len(programs)} programs in {args.dataset_dir}")
        if args.run_dataset:
            summary = DatasetExperiment(args.dataset_report_dir, use_llm=args.llm,
                                        model_name=args.model).run(programs, args.dataset_limit)
            print(f"Dataset experiment complete: {summary['programs']} program(s), "
                  f"{summary['accepted']} accepted change(s).")
            print(f"Report: {os.path.join(args.dataset_report_dir, 'REPORT.md')}")
        return

    # The default presentation flow is interactive: paste C code, then watch the
    # entire autonomous compile/optimize/verify/evaluate process.
    if not args.source_file:
        start_menu(args)
        if not args.no_history_prompt:
            browse_terminal()
        return

    from src.cli.native_report import compile_native_file
    from pathlib import Path
    stdin_input = Path(args.stdin_file).read_text() if args.stdin_file else ""
    if Path(args.source_file).suffix.lower() == ".py" or args.backend == "clang":
        try:
            compile_native_file(args.source_file, language="Python" if Path(args.source_file).suffix.lower() == ".py" else "C",
                                level=args.native_level, python_level=args.python_opt, report_path=args.report,
                                show_output=args.show_output, stdin_input=stdin_input, timeout=args.timeout)
        except (OSError, ValueError, SyntaxError, ClangError) as error:
            parser.exit(1, f"Compilation failed: {error}\n")
        if not args.no_history_prompt:
            browse_terminal()
        return

    if not (args.analyze or args.emit_ir) or args.optimize or args.validate or args.benchmark:
        try:
            run = run_file(os.path.abspath(args.source_file), model_name=args.model,
                           use_llm=args.llm or bool(args.model), report_path=args.report,
                           show_output=args.show_output, benchmark=args.benchmark,
                           iterations=args.iterations, chart=args.chart, diff=args.diff)
        except Exception as error:
            if args.backend == "custom":
                parser.exit(1, f"Custom optimization failed: {error}\n")
            print(f"Custom optimizer unavailable: {error}\nUsing native Clang; custom verification and cost metrics are unavailable.")
            try:
                compile_native_file(args.source_file, level=args.native_level, report_path=args.report,
                                    show_output=args.show_output, stdin_input=stdin_input, timeout=args.timeout)
            except (OSError, ValueError, ClangError) as native_error:
                parser.exit(1, f"Compilation failed: {native_error}\n")
            if not args.no_history_prompt:
                browse_terminal()
            return
        if not args.no_history_prompt:
            browse_terminal()
        if not run.final_verification_passed:
            sys.exit(1)
        return

    cli = CompilerCLI()
    cli.print_banner()

    source_path = os.path.abspath(args.source_file)
    if not os.path.exists(source_path):
        cli.console.print(f"[bold red]Error:[/bold red] File not found: {source_path}")
        sys.exit(1)

    with open(source_path, "r", encoding="utf-8") as f:
        c_source = f.read()

    base_name = os.path.splitext(os.path.basename(source_path))[0]
    run_all = not (args.analyze or args.emit_ir or args.optimize or args.validate or args.benchmark)

    runner = ClangRunner()

    # Step 1: Lexical, Parser, AST, and Semantic Analysis
    if args.analyze or run_all:
        cli.console.print("\n[bold cyan]▶ Step 1: Lexical, AST, and Semantic Analysis[/bold cyan]")
        try:
            lexer = Lexer(c_source)
            tokens = lexer.tokenize()
            parser_obj = Parser(tokens)
            ast = parser_obj.parse()
            printer = ASTPrinter()
            ast_tree = printer.print_tree(ast)

            analyzer = SemanticAnalyzer()
            diags = analyzer.analyze(ast)

            cli.console.print(f"  [green]✓[/green] Tokenized: {len(tokens)} tokens")
            cli.console.print(f"  [green]✓[/green] AST Generated ({len(ast.declarations)} top-level declarations)")
            if diags:
                for d in diags:
                    color = "red" if d.severity == "ERROR" else "yellow"
                    cli.console.print(f"  [{color}]⚠ {d}[/{color}]")
            else:
                cli.console.print("  [green]✓[/green] Semantic Analysis: 0 errors, 0 warnings (Valid)")

            if args.analyze and not run_all:
                cli.console.print("\n[bold magenta]AST Hierarchy Preview:[/bold magenta]")
                cli.console.print("\n".join(ast_tree.splitlines()[:25]))
                return
        except Exception as e:
            cli.console.print(f"[yellow]Frontend parsing notice (using Clang AST):[/yellow] {e}")

    # Step 2: LLVM IR Generation
    with tempfile.TemporaryDirectory() as td:
        ir_unopt_path = os.path.join(td, f"{base_name}_unopt.ll")
        ir_opt_path = os.path.join(td, f"{base_name}_opt.ll")
        bin_base_path = os.path.join(td, f"{base_name}_base.bin")
        bin_opt_path = os.path.join(td, f"{base_name}_opt.bin")
        bin_o1_path = os.path.join(td, f"{base_name}_o1.bin")
        bin_o2_path = os.path.join(td, f"{base_name}_o2.bin")

        cli.console.print("\n[bold cyan]▶ Step 2: LLVM IR Emission & Program Analysis[/bold cyan]")
        runner.compile_to_ir(source_path, ir_unopt_path, opt_level="-O0", disable_optnone=True)
        with open(ir_unopt_path, "r", encoding="utf-8") as f:
            unopt_ir_text = f.read()

        ir_parser = IRParser(unopt_ir_text)
        ir_module = ir_parser.parse()

        total_funcs = len([f for f in ir_module.functions if not f.is_declaration])
        total_blocks = sum(len(f.blocks) for f in ir_module.functions if not f.is_declaration)
        initial_ops = ir_module.total_instructions

        cli.print_program_summary(source_path, total_funcs, total_blocks, initial_ops)

        if args.emit_ir and not run_all:
            cli.console.print(f"\n[bold green]LLVM IR ({initial_ops} instructions):[/bold green]")
            cli.console.print(Syntax(unopt_ir_text[:2000], "llvm", theme="monokai", line_numbers=True))
            return

        # Compile baseline binary
        runner.compile_ir_to_binary(ir_unopt_path, bin_base_path)

        # Step 3: LLM Optimization Agent
        cli.console.print("\n[bold cyan]▶ Step 3: LLM Optimization Agent Analysis[/bold cyan]")
        agent = OptimizationAgent(model_name=args.model)
        cli.console.print(f"  [green]✓[/green] Connecting to agent model: [bold yellow]{agent.active_model}[/bold yellow]")

        proposal = agent.analyze_and_propose(c_source, ir_module, unopt_ir_text)
        cli.print_agent_proposal(proposal, agent.active_model)

        # Step 4: Applying Optimizations
        cli.console.print("\n[bold cyan]▶ Step 4: Applying Guided Compiler Transformations[/bold cyan]")
        pass_mgr = agent.build_pass_pipeline(proposal)
        pass_results = pass_mgr.run(ir_module)
        final_ops = ir_module.total_instructions

        cli.print_pass_results(pass_results, initial_ops, final_ops)

        # Emit optimized LLVM IR
        IREmitter.write_to_file(ir_module, ir_opt_path)
        with open(ir_opt_path, "r", encoding="utf-8") as f:
            opt_ir_text = f.read()

        if args.diff or run_all:
            cli.console.print("\n[bold cyan]▶ LLVM IR Transformation Diff[/bold cyan]")
            cli.print_ir_diff(unopt_ir_text, opt_ir_text)

        # Compile candidate optimized binary
        runner.compile_ir_to_binary(ir_opt_path, bin_opt_path)

        # Step 5: Correctness Verification
        cli.console.print("\n[bold cyan]▶ Step 5: Safety & Correctness Verification[/bold cyan]")
        verifier = CorrectnessVerifier(runner=runner)
        verification_report = verifier.verify(bin_base_path, bin_opt_path)
        cli.print_verification(verification_report)

        if not verification_report.is_valid:
            cli.console.print("[bold red]CRITICAL: Optimization rejected due to correctness failure![/bold red]")
            sys.exit(1)

        # Step 6: Performance Benchmarking
        bench_result = None
        fig_path = None
        if args.benchmark or run_all:
            cli.console.print("\n[bold cyan]▶ Step 6: Performance Benchmarking & Statistical Evaluation[/bold cyan]")
            # Build reference -O1 and -O2 binaries
            try:
                runner.compile_c_to_binary(source_path, bin_o1_path, opt_level="-O1")
                runner.compile_c_to_binary(source_path, bin_o2_path, opt_level="-O2")
            except Exception:
                bin_o1_path = None
                bin_o2_path = None

            benchmarker = Benchmarker(runner=runner, iterations=args.iterations, warmup=3)
            bench_result = benchmarker.run_benchmark(
                baseline_binary=bin_base_path,
                optimized_binary=bin_opt_path,
                clang_o1_binary=bin_o1_path,
                clang_o2_binary=bin_o2_path,
                base_inst_count=initial_ops,
                opt_inst_count=final_ops
            )
            cli.print_benchmark(bench_result)

            # Generate Visualization Chart
            chart_output = args.chart or os.path.join("reports", "figures", f"{base_name}_benchmark.png")
            fig_path = BenchmarkVisualizer.generate_chart(bench_result, base_name, chart_output)
            cli.console.print(f"  [green]✓[/green] Benchmark chart saved: [cyan]{fig_path}[/cyan]")

        # Step 7: Optimization Report
        report_output = args.report or os.path.join("reports", f"optimization_report_{base_name}.md")
        saved_report = cli.generate_markdown_report(
            output_report_path=report_output,
            source_path=source_path,
            c_source=c_source,
            proposal=proposal,
            pass_results=pass_results,
            verification=verification_report,
            benchmark=bench_result,
            figure_path=fig_path
        )
        cli.console.print(f"\n[bold green]✓ Complete Optimization Report generated:[/bold green] [cyan]{saved_report}[/cyan]\n")


if __name__ == "__main__":
    main()
