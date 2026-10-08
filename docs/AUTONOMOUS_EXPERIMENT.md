# Autonomous Experiment Workflow

`python3 main.py --run-dataset` is the reproducible experiment entry point.

For every source program, the orchestrator emits unoptimized LLVM IR and builds a baseline executable. It then tries each optimization pass on a deep copy of the current IR. A candidate follows this state transition:

```text
analyze/pass proposal -> transform copy -> compile -> differential test -> cost score
                                                              |               |
                                                        reject on failure  accept only if lower
```

Differential testing runs the baseline and candidate with 13 argument vectors (a default run plus three edge cases and nine reproducibly randomized values) and checks timeout status, exit code, and stdout. The cost evaluator uses:

```text
weighted cost = instruction count + 3 * expensive arithmetic operations + temporary registers + 10 * mean execution time (ms)
```

The candidate is committed only if both checks pass. Rejected candidates leave the current program unchanged. The loop ends when a complete pass round accepts no candidate or after the configured iteration cap.

Every program produces `reports/dataset/logs/<program>.json`; it includes the opportunity/pass, rationale, verification result, cost before/after, accept/reject decision, final output-match verdict, and pass details. `summary.json` provides all aggregate data behind the report figures.
