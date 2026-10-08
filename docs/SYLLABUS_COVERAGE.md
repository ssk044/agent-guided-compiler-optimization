# Compiler Syllabus Coverage

This project uses a complete C-to-LLVM compilation path and an autonomous optimizer. The optional **TAC and target-assembly learning views** in the interactive menu make the syllabus relationship visible without changing the safe optimization workflow.

| Syllabus area | Project artifact / demonstration |
|---|---|
| Compiler phases | C source → lexical tokens / syntax analysis → semantic analysis → LLVM IR → optimization → target assembly |
| Lexical analysis | `src/lexer/lexer.py` and token definitions in `src/lexer/tokens.py` |
| Syntax analysis | Recursive-descent parser in `src/parser/parser.py`; AST classes in `src/ast/` |
| Symbol tables and semantics | Scoped symbol table and semantic checks in `src/semantic/` |
| Syntax-directed translation | AST and semantic stages lead into intermediate-code generation |
| Three-address code | Optional TAC-style projection of LLVM IR via `src/llvm/tac_renderer.py` |
| Intermediate code | LLVM IR parser/emitter in `src/llvm/`; it is the executable IR optimized by the agent |
| Control flow / basic blocks | LLVM basic blocks, CFG construction, dominators, and loop analysis in `src/analysis/` |
| Common-subexpression elimination | `CommonSubexpressionEliminationPass` |
| Dead-code elimination | `DeadCodeEliminationPass` |
| Constant folding/propagation | `ConstantFoldingPass`, `ConstantPropagationPass` |
| Loop optimization | Loop-invariant code motion and loop analysis |
| Data-flow analysis | Def-use chains, liveness, and memory tracking in `src/analysis/dataflow.py` |
| Target-code generation | Optional target-assembly excerpt generated from final LLVM IR |
| Agent-guided optimization | Analysis specialist, optimization specialist, verifier, cost evaluator, and orchestrator |
| Correctness verification | Differential execution comparison on 13 inputs |

## Important clarification

The project optimizes LLVM IR rather than a hand-written TAC format. LLVM IR fulfills the same role as intermediate code, but it also represents types, basic blocks, memory operations, and control flow. The TAC-style view is provided specifically for teaching and viva discussion.

## Suggested Viva Demonstration

1. Run `python3 main.py`, then choose custom C input.
2. Paste a short program with constants, repeated expressions, and unused code.
3. Choose rule mode for a fast demo.
4. Choose `y` for the TAC/assembly learning views.
5. Explain that the agent optimizes executable LLVM IR; the TAC display is an easy-to-read equivalent representation.
