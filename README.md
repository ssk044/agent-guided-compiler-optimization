# Automated LLM/Agent-Guided Compiler Code Optimization

This project implements a fail-closed compiler-optimization agent for C programs. It uses LLVM IR analyses and optimization passes; an optional Ollama LLM can recommend passes, but it never has authority to commit a transformation.

## One-command presentation demo

```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

The default command opens a menu: choose to paste your own C program, run a quick 10-program dataset demo, or run the full 500-program dataset. For pasted C, type `END` alone on the final line; it then compiles and runs the full autonomous loop immediately.

For the dataset experiment:

```bash
python3 main.py --run-dataset --dataset-limit 10
```

Use the command without `--dataset-limit` for the complete reproducible **500-program** experiment. The first run creates `dataset/programs/`. Results are saved under `reports/dataset/`:

- `REPORT.md` — aggregate metrics
- `summary.json` — machine-readable metrics and every program outcome
- `logs/*.json` — full accept/reject decision log for each program
- `figures/` — Sankey, per-pass outcomes, pie chart, cost-over-iterations, scatter plot, and category heatmap

For a single existing source file:

```bash
python3 main.py examples/05_strength_reduction.c --benchmark --diff
```

## Paste-C-code interactive demo

```bash
ollama pull qwen2.5-coder:3b   # only needed for Qwen guidance
python3 main.py --interactive --llm --model qwen2.5-coder:3b
```

Paste a full C program, then enter `END` on its own line. The terminal asks whether to compile and optimize it, then prints the cost report, source, TAC and LLVM IR before/after for all functions. A decision log is saved to `reports/interactive_decision_log.json`. `--llm` is optional; it asks local Ollama/Qwen to order the available transformations, while the verifier remains the authority.

## Localhost Web UI

The terminal workflow remains the recommended academic demonstration. For a polished browser interface, run:

```bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

Open the local URL printed by Streamlit, normally `http://localhost:8501`. The workbench accepts C and Python, can make a best-effort language detection or use your manual selection, and reports compile/optimization timing. For C, the report includes readable TAC and LLVM IR before and after optimization when the custom optimizer handles the program. After the compiled code, choose whether to view program output. C output comes from the verifier's matching baseline and optimized runs. Python compiles through CPython to bytecode and a version-specific `.pyc`; it only runs if you explicitly choose to view its output. The sidebar lists every model returned by the connected Ollama service, lets you refresh the inventory, and lets you select one for optional C optimization guidance.

## Architecture

1. **Code analysis specialist**: CFG, dominator, loop, def-use, and memory analyses discover opportunities.
2. **Optimization specialist**: rule passes (or optional Ollama proposals) suggest transformations.
3. **Orchestrator**: tests one candidate pass at a time and repeats to a fixed point.
4. **Verification module**: compiles each candidate and performs differential testing across 13 inputs: a default run, edge cases, and reproducible random values. A compile error, timeout, exit-code change, or output mismatch rejects it.
5. **Cost evaluator**: scores `instruction_count + 3 × expensive_arithmetic_ops + temporary_registers + 10 × mean_execution_ms`. A verified candidate is still rejected unless this score decreases.

The acceptance invariant is: **accepted = verified correct AND lower cost**. Since the current IR is updated only after verification succeeds, an incorrect transformation cannot be accepted.

## Dataset

The generator creates 500 small, deterministic C programs:

| Category | Count |
|---|---:|
| Arithmetic-only | 60 |
| Nested expressions | 60 |
| Repeated expressions | 60 |
| Dead code | 60 |
| Loops | 80 |
| Conditionals | 80 |
| Mixed opportunities | 100 |

## Demo Screenshots

The interactive demonstration preserves program output while showing the accepted optimization decisions and compiler artifacts.

### 1. Output Verification and Optimized LLVM IR

![Program output verification and optimized LLVM IR](assets/screenshots/01-output-verification-and-llvm.png)

### 2. LLVM IR and TAC-Style View Before Optimization

![LLVM IR and TAC-style view before optimization](assets/screenshots/02-llvm-and-tac-before.png)

### 3. TAC-Style Intermediate Code After Optimization

![TAC-style view after optimization](assets/screenshots/03-tac-after-optimization.png)

### 4. Target Assembly Excerpt

![Target assembly excerpt](assets/screenshots/04-target-assembly.png)

## Presentation notes

Open the folder in VS Code, use its integrated terminal, install requirements once, then run the quick command above. Open `reports/dataset/REPORT.md` and the generated PNGs after the command completes. For the full run, omit the limit; it takes longer because every candidate must be compiled and differentially tested.

## Full results in Streamlit and VS Code

Both the Streamlit C compiler and terminal C optimizer use the same autonomous,
verified optimization pipeline. Each run shows the selected guidance, weighted
cost before/after, cost saved, percentage reduction, instruction/arithmetic/
temporary counts, execution timings, and verification results. TAC includes all
functions. Both show original C, TAC before/after, LLVM IR before/after, and the
optimized code (LLVM IR; the optimizer does not emit rewritten C).

From the VS Code integrated terminal:

```bash
# Optimize a C file; ask about output after displaying the code
python main.py examples/01_constant_calc.c

# Select any installed Ollama model; display output below the code
python main.py examples/01_constant_calc.c --llm --model qwen2.5-coder:3b --show-output

# Paste C interactively, ending with END on its own line
python main.py --interactive

# Save to a chosen report path; skip the output prompt
python main.py examples/01_constant_calc.c --no-output --report reports/my_run/REPORT.md
```

Without `--show-output` or `--no-output`, the terminal asks whether to display
original and optimized output after the code. This is the default verification
run's captured output. Each file/paste run saves a uniquely named report under
`reports/runs/` and companion artifacts: original C, before/after TAC, before/after
LLVM IR, and `performance.json` containing metrics, timings, and decisions.
An explicit `--report` path writes to that path instead. In Streamlit, use the
performance-report download to retain a run's metrics and decisions. Reports
identify rule fallback in the decisions if model guidance fails.

Weighted cost is an optimization score, not money or model token usage. Runtime
measurements can vary. Python in Streamlit uses CPython bytecode compilation;
the C-specific TAC/LLVM metrics do not apply to Python. If Streamlit falls back
to Clang for unsupported IR, it labels that fallback and leaves custom optimizer
metrics unavailable.

## Complex C and Python programs

For C that uses structs, dynamic memory, recursion, function pointers, sorting,
floating-point operations or constructs unsupported by the educational LLVM
parser, select **Clang native** in Streamlit. It compiles and links the original
and optimized versions using Clang directly. **Auto** tries custom verified
passes first and falls back to native Clang on pipeline errors. Native Clang
shows original C and before/after LLVM IR; custom TAC, model guidance and custom
cost metrics do not apply. Automatic differential tests are not claimed for
native runs. Explicit output execution can supply standard input and a timeout.

The same backends are available in the VS Code terminal:

```bash
python main.py advanced.c --backend clang --show-output
python main.py advanced.c --backend clang --native-level=-O3 --no-output
python main.py advanced.c --backend clang --show-output --stdin-file inputs.txt --timeout 30
python main.py --interactive --backend clang
python main.py advanced.py --show-output
python main.py advanced.py --python-opt 1 --show-output --stdin-file inputs.txt --timeout 30
```

Python accepts the syntax supported by the installed CPython runtime, including
classes, decorators, generators and async functions. Compilation does not run
imports or execute source. The terminal and Streamlit show bytecode before and
after and provide a `.pyc` artifact. Level **0** is the default to preserve
assertions and docstrings; level 1 removes asserts, and level 2 removes docstrings
as well. These levels are CPython compiler options, not automatic algorithm
rewriting or guaranteed speedups. Explicit execution uses the selected level.
Async functions still need the program's normal event-loop entry point.

This is a single-source workbench, not a replacement for arbitrary project build
systems. C projects with custom headers, external libraries or multiple source
files need their build configuration. Python runtime dependencies must already
be installed; pasted Python in Streamlit executes in an isolated temporary
folder, so project-relative imports/files should use the terminal workflow.
Compilation cannot guarantee an improvement for every program or repair invalid
source automatically.

## Previous experiment runs

Streamlit has a **Previous runs** tab at the top, with search and a selector to
reopen saved C/Python runs, source, compiler output, available measurements and
captured program output. Runs are saved once when compilation completes, rather
than on every UI refresh. Explicit program executions attach their output to the
same saved run. History remains available after restarting the app.

Terminal file and pasted-code runs save to the same local history and ask
**View previous experiment runs before exiting?** after processing finishes.
Choose a numbered run to inspect it, then press Enter to leave the history list.
You can also browse history directly:

```bash
python main.py --history
```

For scripts, skip the end-of-run question with `--no-history-prompt` (and use
`--no-output` to skip the execution/output question). History snapshots are stored
in `reports/history/`, anchored to this project directory, so both interfaces
see the same runs. Existing terminal reports under `reports/runs/` also appear.
Earlier Streamlit sessions that were never saved cannot be recovered. History
stores source and captured output locally; opening a saved run never executes it.
