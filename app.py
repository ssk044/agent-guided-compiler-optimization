"""Streamlit compiler workbench for C optimization and Python bytecode compilation."""
from __future__ import annotations

import ast
from dataclasses import asdict
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import streamlit as st

from src.agent.autonomous import AutonomousOrchestrator
from src.agent.ollama_client import OllamaClient
from src.benchmarking.experiment import DatasetExperiment
from src.experiment_history import save_experiment, save_output, list_experiments, run_label, saved_views
from src.compiler import compile_python
from src.compiler.artifacts import assembly_from_ir, save_c_artifacts
from src.compiler.source_optimizer import optimize_c_source
from src.compiler.c_backend import compile_native_c, execute_ir_pair
from src.cli.run_report import render_tac
from src.dataset import DatasetGenerator
from src.llvm import IRParser, TACRenderer
from src.llvm.clang_runner import ClangError, ClangRunner


DEFAULT_SOURCE = """#include <stdio.h>

int main(void) {
    int values[] = {2, 4, 6, 8, 10};
    int total = 0;
    for (int i = 0; i < 5; i++) {
        total += values[i];
    }
    int doubled = total * 2;
    printf("Total: %d\\n", doubled);
    return 0;
}
"""


st.set_page_config(
    page_title="Compiler Studio",
    page_icon="✳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
:root { --ink:#172033; --muted:#69758b; --line:#e5eaf3; --paper:#f5f7fb; --violet:#7357e8; --cyan:#0c9eac; }
html, body, [class*="css"] { font-family:Inter, ui-sans-serif, system-ui, sans-serif; }
.stApp { background: radial-gradient(ellipse at 86% 0%, rgba(126,102,239,.12), transparent 36%), linear-gradient(180deg,#f8f9fd 0%,#f2f5fa 100%); color:var(--ink); }
.block-container { max-width:1440px; padding-top:1.5rem; padding-bottom:4rem; }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#f0f2fa 0%,#f7f8fc 100%); border-right:1px solid #e1e6f0; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color:#25304b; }
[data-testid="stSidebar"] [data-baseweb="select"] * { color:#172033; }
[data-testid="stSidebar"] [data-baseweb="popover"] * { color:#172033; }
.hero { position:relative; overflow:hidden; padding:1.8rem 2rem; border-radius:24px; color:white; background:linear-gradient(115deg,#282d52 0%,#5141a4 56%,#4e89b9 100%); box-shadow:0 18px 45px rgba(40,45,82,.18); }
.hero:after { content:'</>'; position:absolute; right:4%; top:-30px; font:800 170px ui-monospace,monospace; color:rgba(255,255,255,.08); transform:rotate(-9deg); }
.hero-kicker { text-transform:uppercase; letter-spacing:.16em; font-size:.72rem; font-weight:700; color:#c5c9ff; }
.hero h1 { margin:.35rem 0 .3rem; color:white; font-size:2.25rem; letter-spacing:-.04em; }
.hero p { max-width:760px; margin:0; color:#e1e7ff; font-size:1rem; }
.section-label { color:#77839a; text-transform:uppercase; letter-spacing:.13em; font-size:.72rem; font-weight:800; margin:.5rem 0 .45rem; }
.surface { background:rgba(255,255,255,.88); border:1px solid rgba(224,230,241,.95); border-radius:19px; padding:1.15rem 1.25rem; box-shadow:0 8px 24px rgba(33,47,82,.045); }
.status-pill { display:inline-block; padding:.34rem .7rem; border-radius:999px; background:#e5f7f4; color:#087e78; font-size:.76rem; font-weight:800; }
.stButton > button[kind="primary"] { border:0; background:linear-gradient(100deg,#7154e8,#4e76e8); box-shadow:0 9px 22px rgba(99,83,222,.25); }
.stButton > button { border-radius:11px; font-weight:700; }
.stCode, pre, code { font-family:ui-monospace,SFMono-Regular,Menlo,monospace !important; }
.stTabs [data-baseweb="tab-list"] { gap:.55rem; }
.stTabs [data-baseweb="tab"] { border-radius:10px 10px 0 0; }
div[data-testid="stMetric"] { background:white; padding:.9rem 1rem; border:1px solid var(--line); border-radius:14px; box-shadow:0 5px 18px rgba(33,47,82,.04); }
div[data-testid="stMetricLabel"] { color:#727e93; }
div[data-testid="stMetricValue"] { color:#263251; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=20, show_spinner=False)
def available_models(ollama_host: str | None) -> list[str]:
    """Return every model installed in the connected local Ollama instance."""
    return OllamaClient.list_available_models(host=ollama_host)


def detect_language(source: str) -> tuple[str, str]:
    """Best-effort C/Python detection; explicit user selection can override it."""
    text = source.strip()
    if not text:
        return "Unknown", "Add source code to detect a language."

    c_patterns = (
        r"#\s*include\b", r"\b(?:int|char|float|double|void|size_t|struct|typedef)\s+",
        r"\bprintf\s*\(", r"\b(?:malloc|free|scanf|fprintf)\s*\(",
        r"\b(?:unsigned|signed|static|extern)\s+", r"\bmain\s*\([^)]*\)\s*\{",
    )
    if any(re.search(pattern, text) for pattern in c_patterns):
        return "C", "C syntax patterns found."

    try:
        ast.parse(text)
        return "Python", "Valid Python syntax detected."
    except SyntaxError:
        if any(mark in text for mark in ("{", "}", ";", "#include")):
            return "C", "C-style braces, semicolons, or preprocessor syntax found."
        return "Unknown", "Could not confidently identify C or Python; choose a language manually."


def run_c(source: str, use_llm: bool, model_name: str | None, backend: str = "Auto", native_level: str = "-O2") -> dict:
    if backend == "Clang native":
        return compile_native_c(source, native_level)
    with tempfile.TemporaryDirectory(prefix="compiler_studio_c_") as directory:
        source_path = Path(directory) / "program.c"
        source_path.write_text(source, encoding="utf-8")
        try:
            run = AutonomousOrchestrator(use_llm=use_llm, model_name=model_name).optimize_file(str(source_path))
        except Exception as optimizer_error:
            if backend == "Custom passes":
                raise
            result = compile_native_c(source, native_level)
            result["fallback_reason"] = str(optimizer_error)
            return result

    return {
        **optimize_c_source(source),
        "language": "C",
        "source": source,
        "model": model_name if use_llm else "Rule-based optimizer",
        "initial_breakdown": asdict(run.initial_cost),
        "final_breakdown": asdict(run.final_cost),
        "decisions": [asdict(decision) for decision in run.decisions],
        "code": run.final_ir,
        "optimized_assembly": assembly_from_ir(run.final_ir),
        "initial_ir": run.initial_ir,
        "baseline_output": run.baseline_output,
        "optimized_output": run.optimized_output,
        "timings": run.timings,
        "verification_passed": run.final_verification_passed,
        "tests_passed": run.verification_tests_passed,
        "tests_run": run.verification_tests_run,
        "accepted": run.accepted,
        "initial_cost": run.initial_cost.weighted_cost,
        "final_cost": run.final_cost.weighted_cost,
        "reduction_percent": run.reduction_percent,
        "custom_optimizer": True,
        "extension": "ll",
        "mime": "text/plain",
        "output_label": "Optimized LLVM IR",
    }


def run_python(source: str, optimization_level: int) -> dict:
    result = compile_python(source, optimization_level=optimization_level, filename="program.py")
    baseline = compile_python(source, optimization_level=0, filename="program.py")
    return {
        "language": "Python",
        "code": result.bytecode_listing,
        "source": source,
        "pyc": result.pyc_bytes,
        "baseline_bytecode": baseline.bytecode_listing,
        "timings": {"source_compile_seconds": result.compile_seconds, "total_seconds": result.elapsed_seconds},
        "optimization_level": result.optimization_level,
        "extension": "pyc",
        "mime": "application/octet-stream",
        "output_label": "CPython bytecode listing",
    }


def execute_python_for_output(source: str, optimization_level: int = 0, stdin_input: str = "", timeout: float = 5) -> tuple[str, str, int | None]:
    """Run Python source only after the user explicitly requests its output."""
    with tempfile.TemporaryDirectory(prefix="compiler_studio_python_run_") as directory:
        source_path = Path(directory) / "program.py"
        source_path.write_text(source, encoding="utf-8")
        try:
            completed = subprocess.run(
                [sys.executable, "-I", *(["-O"] if optimization_level == 1 else ["-OO"] if optimization_level == 2 else []), str(source_path)],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=timeout,
                input=stdin_input,
                check=False,
            )
            return completed.stdout, completed.stderr, completed.returncode
        except subprocess.TimeoutExpired as error:
            stdout = error.stdout.decode(errors="replace") if isinstance(error.stdout, bytes) else (error.stdout or "")
            stderr = error.stderr.decode(errors="replace") if isinstance(error.stderr, bytes) else (error.stderr or "")
            return stdout, stderr + f"\nStopped: program exceeded the {timeout}-second limit.", None


def show_compile_result(result: dict, show_code: bool) -> None:
    timings = result["timings"]
    lang = result["language"]
    st.markdown('<div class="section-label">Compile report</div>', unsafe_allow_html=True)
    if lang == "C":
        if result["custom_optimizer"]:
            metrics = st.columns(4)
            metrics[0].metric("Total pipeline", f"{timings['total_seconds']:.3f} s")
            metrics[1].metric("Source compilation", f"{timings['source_compile_seconds']:.3f} s")
            metrics[2].metric("Optimization", f"{timings['optimization_seconds']:.3f} s")
            metrics[3].metric("Final verification", f"{timings['final_verification_seconds']:.3f} s")
            verdict = "Verified" if result["verification_passed"] else "Verification failed"
            st.markdown(f'<span class="status-pill">{verdict}</span> &nbsp; {result["tests_passed"]}/{result["tests_run"]} test cases matched', unsafe_allow_html=True)
            st.markdown("**Optimization effectiveness for this run**")
            st.write(f"Selected guidance: **{result['model']}**")
            before_cost, after_cost = result["initial_breakdown"], result["final_breakdown"]
            scores = st.columns(4)
            scores[0].metric("Weighted cost · before", f"{result['initial_cost']:.2f}")
            scores[1].metric("Weighted cost · after", f"{result['final_cost']:.2f}")
            scores[2].metric("Cost reduction", f"{result['reduction_percent']:.1f}%")
            scores[3].metric("Cost saved", f"{result['initial_cost'] - result['final_cost']:.2f}")
            st.table([
                {"Measure": label, "Before": before_cost[key], "After": after_cost[key],
                 "Reduction": before_cost[key] - after_cost[key]}
                for key, label in [("instructions", "LLVM instructions"), ("arithmetic", "Arithmetic operations"),
                                   ("temporaries", "Temporary values"), ("runtime_ms", "Measured execution time (ms)")]
            ])
            st.caption("Weighted cost = instructions + 3 × arithmetic operations + temporary values + 10 × execution time in ms. This is an optimization score, not a monetary or model usage cost. Execution timings can vary between runs.")
            st.caption(f"Accepted optimizations: {result['accepted']}. Model guidance suggests pass order; verified compiler passes produce the changes.")
            with st.expander("Optimization decisions and guidance used"):
                st.dataframe(result["decisions"], use_container_width=True)
            st.download_button("Download this run's performance report", data=json.dumps({
                key: result[key] for key in ("model", "initial_breakdown", "final_breakdown", "reduction_percent",
                                            "accepted", "verification_passed", "tests_passed", "tests_run", "timings", "decisions")
            }, indent=2), file_name="optimization_report.json", mime="application/json")
            with st.expander("Pipeline timing breakdown"):
                st.write("Source compile = C to LLVM IR plus baseline executable. Optimization = analysis, candidate compilation, verification and cost evaluation. Final verification = comparing baseline and final executables.")
                st.json({key: round(value, 4) for key, value in timings.items()})
        else:
            metrics = st.columns(3)
            metrics[0].metric("Total compile", f"{timings['total_seconds']:.3f} s")
            metrics[1].metric("Backend", result.get("backend", "Clang"))
            metrics[2].metric("Differential tests", "Not run")
            st.info("Clang compiled and linked the program using its native optimizer. Model guidance and custom cost metrics do not apply to this backend. Differential verification has not been run.")
            if result.get("fallback_reason"):
                with st.expander("Why the fallback was used"):
                    st.code(result["fallback_reason"], language="text")
    else:
        metrics = st.columns(3)
        metrics[0].metric("Compile time", f"{timings['source_compile_seconds']:.4f} s")
        metrics[1].metric("Total build time", f"{timings['total_seconds']:.4f} s")
        metrics[2].metric("CPython optimize level", str(result["optimization_level"]))
        st.caption("Python source was compiled to bytecode, not executed. CPython applies its built-in optimizations; the project’s custom LLVM passes are C-only.")

    fingerprint = result.get("fingerprint", hashlib.sha256(result["code"].encode()).hexdigest()[:8])
    if show_code:
        if lang == "C" and result["custom_optimizer"]:
            st.markdown('<div class="section-label">Understand the optimized program</div>', unsafe_allow_html=True)
            st.caption("Start with the readable TAC-style view. LLVM IR is the lower-level compiler representation; compare its before and after versions in the other tabs.")
            code_tabs = st.tabs(["TAC · after", "TAC · before", "LLVM IR · after", "LLVM IR · before", "Original source", "Optimized code · assembly", "Optimized C source"])
            with code_tabs[0]:
                st.code(render_tac(result["code"]), language="text", line_numbers=True)
            with code_tabs[1]:
                st.code(render_tac(result["initial_ir"]), language="text", line_numbers=True)
            with code_tabs[2]:
                st.code(result["code"], language="llvm", line_numbers=True)
            with code_tabs[3]:
                st.code(result["initial_ir"], language="llvm", line_numbers=True)
            with code_tabs[4]:
                st.code(result["source"], language="c", line_numbers=True)
            with code_tabs[5]:
                st.caption("Assembly generated from the optimized LLVM IR. The C source tab uses a separate conservative source optimizer.")
                st.code(result.get("optimized_assembly", "Recompile to generate assembly for this run."), language="asm", line_numbers=True)
            with code_tabs[6]:
                st.caption(result.get("source_optimization_note", "Recompile to generate the C source view."))
                st.code(result.get("optimized_source", result["source"]), language="c", line_numbers=True)
        elif lang == "C":
            native_tabs = st.tabs(["Original C", "LLVM IR · before", "Optimized LLVM IR", "Optimized code · assembly", "Optimized C source"])
            for tab, code, language in zip(native_tabs, [result["source"], result["initial_ir"], result["code"], result.get("optimized_assembly", "Recompile to generate assembly for this run."), result.get("optimized_source", result["source"])], ["c", "llvm", "llvm", "asm", "c"]):
                with tab:
                    st.code(code, language=language, line_numbers=True)
            st.caption(result.get("source_optimization_note", "Recompile to generate the C source view."))
            st.caption("Native Clang supports constructs beyond the educational TAC parser. TAC and custom cost scores are unavailable for this backend.")
        else:
            st.markdown('<div class="section-label">Python compile output</div>', unsafe_allow_html=True)
            python_tabs = st.tabs(["Readable source", "Bytecode · after", "Bytecode · before (level 0)"])
            with python_tabs[0]:
                st.code(result["source"], language="python", line_numbers=True)
                st.caption("This is the input source. CPython does not emit rewritten Python source.")
            with python_tabs[1]:
                st.code(result["code"], language="text", line_numbers=True)
            with python_tabs[2]:
                st.code(result["baseline_bytecode"], language="text", line_numbers=True)
        if lang == "C" and result.get("optimized_assembly"):
            st.caption("Download C source, LLVM IR, and target assembly separately.")
            if result.get("optimized_source"):
                st.download_button("Download optimized C source (.c)", result["optimized_source"],
                                   file_name="optimized.c", mime="text/plain", key=f"c_source_{fingerprint}")
            st.download_button("Download optimized assembly (.s)", result["optimized_assembly"],
                               file_name="optimized.s", mime="text/plain", key=f"assembly_{fingerprint}")
            if result.get("artifact_dir"):
                st.caption(f"Open this folder in VS Code to view both outputs: {result['artifact_dir']}")
        st.download_button(
            f"Download compiled {lang} output (.{result['extension']})",
            data=result.get("pyc", result["code"]),
            file_name=f"compiled_program.{result['extension']}",
            mime=result["mime"],
            key=f"download_{lang}_{hashlib.sha256(result['code'].encode()).hexdigest()[:8]}",
        )
        st.markdown('<div class="section-label">Program output</div>', unsafe_allow_html=True)
        wants_output = st.radio(
            "Would you like to see the program output?",
            ["No", "Yes"],
            horizontal=True,
            index=0,
            key=f"show_program_output_{fingerprint}",
        )
        if wants_output == "Yes" and lang == "C":
            if result["custom_optimizer"]:
                before, after = st.columns(2)
                before.markdown("**Original program · default verification run**")
                before.code(result["baseline_output"] or "(no output)", language="text")
                after.markdown("**Optimized program · same run**")
                after.code(result["optimized_output"] or "(no output)", language="text")
            else:
                stdin_input = st.text_area("Standard input for C program", key=f"c_stdin_{fingerprint}")
                timeout = st.number_input("C execution timeout (seconds)", min_value=1, max_value=60, value=5, key=f"c_timeout_{fingerprint}")
                if st.button("Run original and optimized C", key=f"native_run_{fingerprint}"):
                    try:
                        outputs = execute_ir_pair(result["initial_ir"], result["code"], stdin_input, timeout)
                        if result.get("history_id"):
                            save_output(result["history_id"], {"stdin": stdin_input, "timeout": timeout,
                                **{name: {"stdout": item.stdout, "stderr": item.stderr, "exit_code": item.returncode,
                                          "timed_out": item.timed_out} for name, item in outputs.items()}})
                        for label in ("before", "after"):
                            execution = outputs[label]
                            st.write(f"{label.title()} · exit {execution.returncode}")
                            st.code(execution.stdout or "(no output)", language="text")
                            if execution.stderr:
                                st.code(execution.stderr, language="text")
                        matched = all(not item.timed_out and item.returncode == 0 for item in outputs.values()) and outputs["before"].stdout == outputs["after"].stdout and outputs["before"].stderr == outputs["after"].stderr
                        st.info("This input matched." if matched else "This input did not complete successfully with matching output.")
                    except ClangError as error:
                        st.error(str(error))
        elif wants_output == "Yes" and lang == "Python":
            st.warning("This runs the Python source you entered on this computer. Only continue with code you trust; execution uses the timeout below.")
            stdin_input = st.text_area("Standard input for Python program", key=f"py_stdin_{fingerprint}")
            timeout = st.number_input("Python execution timeout (seconds)", min_value=1, max_value=60, value=5, key=f"py_timeout_{fingerprint}")
            if st.button("Run Python and show output", key=f"run_python_output_{fingerprint}"):
                stdout, stderr, exit_code = execute_python_for_output(result["source"], result["optimization_level"], stdin_input, timeout)
                st.session_state[f"python_output_{fingerprint}"] = (stdout, stderr, exit_code)
                if result.get("history_id"):
                    save_output(result["history_id"], {"stdout": stdout, "stderr": stderr, "exit_code": exit_code,
                                                       "stdin": stdin_input, "timeout": timeout})
            python_output = st.session_state.get(f"python_output_{fingerprint}")
            if python_output:
                stdout, stderr, exit_code = python_output
                st.markdown(f"**Exit status:** `{exit_code if exit_code is not None else 'timed out'}`")
                st.code(stdout or "(no standard output)", language="text")
                if stderr:
                    st.markdown("**Errors / diagnostics**")
                    st.code(stderr, language="text")
    else:
        st.info("Compilation completed. Turn on ‘Show compiled output’ in the sidebar to display the result.")


st.markdown("""
<div class="hero">
  <div class="hero-kicker">Compiler workbench · C + Python</div>
  <h1>Compile. Optimize. Inspect.</h1>
  <p>A clean workspace for compiling C through the project’s LLVM optimizer and Python through CPython bytecode, with measured timings and local model guidance.</p>
</div>
""", unsafe_allow_html=True)
st.write("")

ollama_host = os.environ.get("OLLAMA_HOST")
with st.sidebar:
    st.markdown("## Workbench settings")
    st.markdown('<div class="section-label">Compiler</div>', unsafe_allow_html=True)
    language_choice = st.selectbox("Source language", ["Auto-detect", "C", "Python"], index=0, key="language_choice")
    source_hint = st.session_state.get("source_code", DEFAULT_SOURCE)
    inferred_hint, _ = detect_language(source_hint)
    optimization_disabled = language_choice == "C" or (language_choice == "Auto-detect" and inferred_hint == "C")
    optimization_level = st.select_slider("Python optimization", options=[0, 1, 2], value=0, disabled=optimization_disabled, help="CPython optimize levels: 0 keeps asserts, 1 removes asserts, 2 also removes docstrings.")
    c_backend = st.selectbox("C optimization backend", ["Auto", "Clang native", "Custom passes"], help="Choose Clang native for complex C, pointers, structs, recursion and large functions. Auto tries custom passes first.")
    native_level = st.selectbox("Native C optimization", ["-O2", "-O3", "-O1", "-Os"])
    show_compiled_output = st.toggle("Show compiled output", value=True)
    st.divider()
    st.markdown('<div class="section-label">Local model assistance</div>', unsafe_allow_html=True)
    use_llm = st.toggle("Use Ollama model guidance", value=False, help="The model only suggests pass order. Verification still controls acceptance.")
    installed_models = available_models(ollama_host)
    if installed_models:
        st.success(f"Ollama connected · {len(installed_models)} model{'s' if len(installed_models) != 1 else ''} found")
    else:
        st.warning("No Ollama models detected")
    refresh_models = st.button("Refresh model list", use_container_width=True, help="Reload all models installed in the connected Ollama instance.")
    if refresh_models:
        available_models.clear()
        st.rerun()
    model_name = None
    model_options = installed_models or ["No installed models"]
    model_name = st.selectbox(
        "Model for pass-order suggestions",
        model_options,
        disabled=not use_llm or not installed_models,
        help="Every installed model returned by Ollama appears here. The selected model only suggests safe pass order.",
    ) if installed_models else None
    if use_llm and not installed_models:
        st.caption("Start Ollama, install a model, then refresh this list. The rule-based optimizer remains available.")
    st.divider()
    st.caption("C verification runs compiled programs locally. Python is compiled first; execution happens only if you choose to view its output.")


compiler_tab, history_tab, dataset_tab, guide_tab = st.tabs(["Compiler", "Previous runs", "Benchmark lab", "How it works"])
with compiler_tab:
    left, right = st.columns([1.55, 1], gap="large")
    with left:
        st.markdown('<div class="section-label">Source editor</div>', unsafe_allow_html=True)
        source = st.text_area("Source code", value=DEFAULT_SOURCE, height=410, key="source_code", label_visibility="collapsed", placeholder="Paste a C or Python program…")
        detected_language, detection_detail = detect_language(source)
        chosen_language = detected_language if language_choice == "Auto-detect" else language_choice
        lang_color = "#087e78" if chosen_language in {"C", "Python"} else "#a16305"
        st.markdown(f'<span class="status-pill" style="background:#eef0ff;color:{lang_color}">{chosen_language}</span> &nbsp; <span style="color:#77839a">{detection_detail}</span>', unsafe_allow_html=True)
        if language_choice != "Auto-detect" and detected_language not in {"Unknown", language_choice}:
            st.warning(f"The source looks like {detected_language}, while {language_choice} is selected. You can switch to Auto-detect or change the language.")
    with right:
        st.markdown('<div class="section-label">Build configuration</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("**Target pipeline**")
            st.write("C → LLVM IR → custom verified passes or native Clang optimization")
            st.write("Python → CPython parser → optimized bytecode")
            if chosen_language == "C":
                st.warning("C verification runs your program on test inputs. Only compile source you trust.")
                if use_llm and not installed_models:
                    st.info("LLM guidance is unavailable until Ollama has a model installed. The rule-based optimizer will still work.")
            elif chosen_language == "Python":
                st.info("The Python compiler accepts Python syntax supported by this Python runtime. Compilation does not execute your program.")
        st.write("")
        compile_clicked = st.button("Compile and optimize", type="primary", use_container_width=True, disabled=chosen_language == "Unknown" or not source.strip())
        if chosen_language == "Unknown":
            st.caption("Choose C or Python manually, or enter recognizable source code.")

    source_fingerprint = hashlib.sha256(f"{chosen_language}:{optimization_level}:{c_backend}:{native_level}:{use_llm}:{model_name if use_llm else None}:{source}".encode()).hexdigest()
    if compile_clicked:
        try:
            if chosen_language == "C":
                with st.spinner("Compiling C, optimizing LLVM IR, and verifying candidate changes…"):
                    result = run_c(source, use_llm and bool(installed_models), model_name if use_llm and installed_models else None, c_backend, native_level)
            else:
                with st.spinner("Parsing Python and generating bytecode…"):
                    result = run_python(source, optimization_level)
            result["fingerprint"] = source_fingerprint
            result.setdefault("source", source)
            result.setdefault("model", "CPython" if chosen_language == "Python" else "Clang")
            if chosen_language == "C":
                from uuid import uuid4
                result["artifact_dir"] = str(save_c_artifacts(
                    result, Path("reports/streamlit") / uuid4().hex))
            result["history_id"] = save_experiment(result, interface="Streamlit", source_name="Pasted program")
            st.session_state["compiler_result"] = result
            st.session_state.pop("compiler_error", None)
        except ClangError as error:
            st.session_state.pop("compiler_result", None)
            st.session_state["compiler_error"] = ("Compilation failed", error.stderr.strip() or str(error))
        except (SyntaxError, ValueError) as error:
            st.session_state.pop("compiler_result", None)
            st.session_state["compiler_error"] = ("Source could not be compiled", str(error))
        except Exception as error:
            st.session_state.pop("compiler_result", None)
            st.session_state["compiler_error"] = ("Compiler pipeline could not complete", str(error))

    result = st.session_state.get("compiler_result")
    error = st.session_state.get("compiler_error")
    if error:
        st.error(error[0])
        st.code(error[1], language="text")
    elif result and result.get("fingerprint") == source_fingerprint:
        show_compile_result(result, show_compiled_output)
    elif result:
        st.info("Source changed since the last run. Compile again to refresh the report.")


with history_tab:
    st.subheader("Previous experiment runs")
    st.caption("Saved locally across restarts. Includes Streamlit and terminal runs. Opening a run never executes its code. Times are shown in India Standard Time.")
    st.button("Refresh history", key="refresh_history")
    search = st.text_input("Search previous runs", placeholder="Model, language, or source name")
    records = [record for record in list_experiments() if search.casefold() in run_label(record).casefold()]
    if not records:
        st.info("No matching saved runs yet. Compile a program to add one.")
    else:
        record = st.selectbox("Choose a previous run", records, format_func=run_label, key="selected_history_run")
        snapshot = record["result"]
        if snapshot:
            st.write(f"**Language:** {snapshot.get('language', 'Unknown')} · **Guidance/backend:** {snapshot.get('model', snapshot.get('backend', 'Unknown'))}")
            if snapshot.get("initial_cost") is not None:
                cols = st.columns(3)
                cols[0].metric("Weighted cost before", f"{snapshot['initial_cost']:.2f}")
                cols[1].metric("Weighted cost after", f"{snapshot['final_cost']:.2f}")
                cols[2].metric("Cost reduction", f"{snapshot['reduction_percent']:.2f}%")
            with st.expander("Saved measurements and decisions", expanded=True):
                st.json({key: value for key, value in snapshot.items() if key not in ("source", "code", "initial_ir", "baseline_bytecode", "fingerprint")})
            for title, code, language in saved_views(snapshot):
                with st.expander(title):
                    st.code(code, language=language, line_numbers=True)
            st.download_button("Download saved run", json.dumps(record, indent=2), file_name=f"experiment_{record['id']}.json", mime="application/json")
        if record.get("report_text"):
            with st.expander("Saved terminal report"):
                st.code(record["report_text"], language="markdown")


with dataset_tab:
    st.markdown('<div class="section-label">Existing compiler benchmark</div>', unsafe_allow_html=True)
    st.subheader("Generated C benchmark suite")
    st.write("Generate and run the project’s existing benchmark programs to compare optimization outcomes.")
    dataset_size = st.radio("Experiment size", ["Quick demo · 10 programs", "Full run · 500 programs"], horizontal=True)
    if st.button("Run benchmark experiment", use_container_width=True):
        limit = 10 if dataset_size.startswith("Quick") else None
        with st.spinner("Generating programs and running the experiment. The full run can take several minutes."):
            programs = DatasetGenerator("dataset/programs").generate()
            output_dir = "reports/ui_dataset"
            summary = DatasetExperiment(output_dir, use_llm=use_llm and bool(installed_models), model_name=model_name if use_llm and installed_models else None).run(programs, limit)
        st.success(f"Finished {summary['programs']} programs.")
        st.json(summary)
        figures = sorted((Path(output_dir) / "figures").glob("*.png"))
        for figure in figures:
            st.image(str(figure), caption=figure.stem.replace("_", " ").title(), use_container_width=True)


with guide_tab:
    st.subheader("Two compiler paths, one workbench")
    st.markdown("""
**C path:** Clang generates LLVM IR. The project analyzes the IR, applies registered optimization passes, compiles candidate versions, verifies behavior with differential tests, and accepts only verified cost improvements. If the custom IR pipeline cannot handle a Clang-supported construct, the workbench falls back to Clang `-O2` and clearly marks that custom differential verification was not run. Timing separates available build stages.

**Native C path:** Select Clang native for complex constructs such as structs, pointer arithmetic, recursion, function pointers and floating-point operations. This backend compiles and links before/after LLVM IR without running the custom IR parser. It does not provide custom TAC/cost scores or automatic differential verification. Standard input and a timeout can be supplied when explicitly running the programs. Auto falls back to this backend if the custom pipeline fails. External headers, libraries and multi-file projects still require their normal build setup.

**Python path:** CPython parses the source and compiles it to bytecode with the selected optimization level. The page displays a bytecode listing and offers a version-specific `.pyc` download. Python currently uses CPython's built-in optimizer; the custom LLVM optimization agent applies to C only.

**Language detection:** Auto-detect uses C syntax markers and Python parsing as a best effort. Choose C or Python manually when snippets are ambiguous. The selected compiler reports syntax and compilation errors.

**Local models:** The sidebar lists models installed on the connected Ollama server. Refresh after installing a model. LLM guidance only reorders safe optimization passes, and verification remains authoritative.
    """)
