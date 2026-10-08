# Architecture Specification: LLM-Guided Compiler Optimization System

## 1. System Overview

The **LLM-Guided Compiler Optimization System** is a production-grade compilation pipeline that bridges classical compiler theory with local Large Language Model (LLM) agents.

Rather than relying on generative models to rewrite C/C++ source code directly (which frequently introduces syntax errors, semantic regressions, or subtle memory safety bugs), this system uses the LLM as an **intelligent optimizer agent** operating at the **LLVM Intermediate Representation (IR)** level.

```
+-----------------------------------------------------------------------------------------+
|                                    COMPILATION PIPELINE                                  |
+-----------------------------------------------------------------------------------------+
|                                                                                         |
|   +-------------------+       +--------------------+       +--------------------+       |
|   |  C/C++ Source     | ----> | Lexical Analysis   | ----> |  Recursive-Descent |       |
|   |  (*.c, *.cpp)     |       | & Token Stream     |       |  Parser & AST      |       |
|   +-------------------+       +--------------------+       +--------------------+       |
|                                                                      |                  |
|                                                                      v                  |
|   +-------------------+       +--------------------+       +--------------------+       |
|   | LLVM IR Emission  | <---- | Clang Frontend     | <---- | Semantic Analysis  |       |
|   | (-O0 + Names)     |       | Bridge             |       | & Symbol Scoping   |       |
|   +-------------------+       +--------------------+       +--------------------+       |
|             |                                                                           |
|             v                                                                           |
|   +-------------------+       +--------------------+       +--------------------+       |
|   | CFG & Dominator   | ----> | Natural Loop &     | ----> | LLM Optimization   |       |
|   | Construction      |       | Liveness Analysis  |       | Agent (Qwen 3B)    |       |
|   +-------------------+       +--------------------+       +--------------------+       |
|                                                                      |                  |
|                                                                      v                  |
|   +-------------------+       +--------------------+       +--------------------+       |
|   | Clang Assembler   | <---- | LLVM IR Emitter    | <---- | Custom IR Pass     |       |
|   | & Native Linker   |       | & Serialization    |       | Engine (DCE/CF/SR) |       |
|   +-------------------+       +--------------------+       +--------------------+       |
|             |                                                                           |
|             v                                                                           |
|   +-------------------+       +--------------------+       +--------------------+       |
|   | Differential      | ----> | High-Precision     | ----> | Markdown & Plot    |       |
|   | Verifier (Safety) |       | Benchmarking       |       | Report Generation  |       |
|   +-------------------+       +--------------------+       +--------------------+       |
|                                                                                         |
+-----------------------------------------------------------------------------------------+
```

---

## 2. Component Architecture

### 2.1 Lexer (`src/lexer/`)
- **Tokens (`tokens.py`):** Enumerates all terminal symbols in standard C: keywords (`int`, `float`, `if`, `while`, `for`, `return`, `const`, `void`), operators (`+`, `-`, `*`, `/`, `%`, `==`, `!=`, `<`, `>`, `&&`, `||`, `<<`, `>>`), punctuation, and literals.
- **Lexer (`lexer.py`):** Scans the source buffer with full line and column coordinate tracking. Handles multi-character operators, comments (`//` and `/* ... */`), string/character escape sequences, and preprocessor directives.

### 2.2 Parser & AST (`src/parser/`, `src/ast/`)
- **Node Hierarchy (`nodes.py`):** Dataclasses representing `ProgramNode`, `FunctionDefNode`, `ParamNode`, `VarDeclNode`, `BlockNode`, `AssignmentNode`, `BinaryOpNode`, `UnaryOpNode`, `LiteralNode`, `VariableNode`, and structured control-flow statements (`IfStmtNode`, `WhileStmtNode`, `ForStmtNode`, `ReturnStmtNode`, `FunctionCallNode`).
- **Parser (`parser.py`):** Recursive-descent parser with operator precedence climbing. Handles variable declarations, function definitions, parameter lists (including array brackets `argv[]`), and nested expressions.
- **AST Visitor & Pretty Printer (`visitor.py`):** Implements the Visitor design pattern. Produces hierarchical tree representations for visual terminal inspection.

### 2.3 Semantic Analysis (`src/semantic/`)
- **Symbol Table (`symbol_table.py`):** Lexically scoped symbol table supporting nested scopes, variable definitions, type information, and reference counters.
- **Analyzer (`analyzer.py`):** Validates declaration before use, prevents variable re-declarations within the same scope, flags unreachable statements following unconditional returns, detects division by zero, and warns about unused variables.

### 2.4 LLVM IR Infrastructure (`src/llvm/`)
- **Clang Runner (`clang_runner.py`):** Interfaces with system Clang. Emits textual LLVM IR with `-O0 -Xclang -disable-O0-optnone -fno-discard-value-names`. Compiles LLVM IR (`.ll`) to native target binaries (`arm64` or `x86_64`).
- **IR Data Structures (`ir_nodes.py`):** Python object model for LLVM IR modules, functions, basic blocks, instructions, and typed operands.
- **IR Parser (`ir_parser.py`):** Parses Clang textual LLVM IR into the object model. Automatically canonicalizes numeric variables (`%0 -> %_t0`) and numeric labels (`12: -> bb_12:`) so that instructions can be safely inserted or deleted without violating LLVM's sequential numbering requirement.
- **IR Emitter (`ir_emitter.py`):** Serializes transformed IR modules back to valid textual LLVM IR that compiles cleanly with Clang.

### 2.5 Program Analysis (`src/analysis/`)
- **Control-Flow Graph (`cfg.py`):** Constructs directed graphs of basic blocks, tracks predecessors and successors, identifies entry and exit blocks, and computes reachability to detect dead basic blocks.
- **Dominator Analysis (`dominators.py`):** Computes dominator sets $Dom(n)$, immediate dominators $idom(n)$, dominator tree child sets, and dominance frontiers $DF(n)$ using iterative data-flow equations.
- **Loop Analysis (`loop_analysis.py`):** Identifies natural loops via back-edges $A \to B$ where $B$ dominates $A$. Extracts loop headers, latches, loop bodies, exit blocks, preheaders, and identifies loop-invariant computations.
- **Data-Flow Analysis (`dataflow.py`):** Computes Def-Use / Use-Def chains, iterative backwards Liveness Analysis ($USE$, $DEF$, $IN$, $OUT$), and tracks memory allocations (`alloca`) alongside their corresponding `store` and `load` operations.

### 2.6 Optimization Passes (`src/optimizations/`)
- **Constant Folding (`constant_folding.py`):** Evaluates arithmetic (`add`, `sub`, `mul`, `sdiv`, `shl`, `and`, `or`, `xor`) and comparisons (`icmp`) with constant operands at compile-time.
- **Constant Propagation (`constant_propagation.py`):** Propagates known constant values across registers and single-assignment memory allocas directly into reading `load` instructions.
- **Dead-Code Elimination (`dead_code_elimination.py`):** Recursively eliminates unreferenced pure instructions, dead stores to memory locations that are never loaded, unreferenced `alloca` allocations, and unreachable basic blocks.
- **Common Subexpression Elimination (`common_subexpression_elimination.py`):** Value-numbers pure binary operations and eliminates duplicate calculations if a dominating identical computation is available.
- **Strength Reduction (`strength_reduction.py`):** Lowers hardware-expensive operations to cheaper instructions (e.g. `x * 2^k -> x << k`, `x / 2^k -> x >> k`, `x * 1 -> x`, `x + 0 -> x`, `x * 0 -> 0`, `x ^ x -> 0`).
- **Loop-Invariant Code Motion (`loop_invariant_code_motion.py`):** Hoists computations inside loop bodies that depend solely on external or constant values into the loop's preheader.

### 2.7 LLM Optimization Agent (`src/agent/`)
- **Ollama Client (`ollama_client.py`):** Connects to local Ollama runtime. Dynamically discovers models (`qwen2.5-coder:3b`, `qwen2.5:3b`, `tinyllama`). Enforces strict JSON grammar mode (`format="json"`).
- **Agent Orchestrator (`optimization_agent.py`):** Feeds program source, LLVM IR, CFG metrics, loop nests, and candidate patterns to the LLM. Parses and validates the response against strict Pydantic schemas (`schema.py`). Translates the agent's proposal into an executable pass pipeline.

### 2.8 Correctness Verification (`src/validation/`)
- **Differential Verifier (`verifier.py`):** Runs baseline and candidate optimized binaries against a suite of input vectors. Compares:
  1. Exit codes (`returncode`).
  2. Standard output (exact text or numerical float comparison within $10^{-5}$ tolerance).
  3. Timeout safety (ensures optimizations do not cause infinite loops).
- **Fail-Safe Mechanism:** If ANY discrepancy is detected, the candidate IR is immediately rolled back and the optimization is formally rejected with diagnostic logs.

### 2.9 Benchmarking & Reporting (`src/benchmarking/`, `src/cli/`)
- **Benchmarker (`benchmark.py`):** Executes warmup iterations followed by $N$ high-resolution monotonic clock measurements. Computes Mean, Median, Standard Deviation, and Speedup percentage.
- **Visualizer (`visualizer.py`):** Uses Matplotlib to render dark-themed dual-panel figures displaying runtime latency (with error bars) and IR instruction reduction.
- **Report Generator (`interface.py`):** Generates Markdown summaries with pass logs, test reports, and LinkedIn-ready snippets.
