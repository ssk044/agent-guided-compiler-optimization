"""
Unit tests for CFG, Dominators, Loops, and Dataflow Analysis.
"""
import os
import tempfile
from src.llvm import ClangRunner, IRParser
from src.analysis import ControlFlowGraph, DominatorAnalysis, LoopAnalysis, DefUseAnalysis, LivenessAnalysis


def test_cfg_and_dominators():
    code = """
    int branch_test(int x) {
        int r = 0;
        if (x > 10) {
            r = 100;
        } else {
            r = 200;
        }
        return r;
    }
    """
    runner = ClangRunner()
    with tempfile.TemporaryDirectory() as td:
        c_path = os.path.join(td, "branch.c")
        ll_path = os.path.join(td, "branch.ll")
        with open(c_path, "w") as f:
            f.write(code)
        runner.compile_to_ir(c_path, ll_path)
        module = IRParser(open(ll_path).read()).parse()
        fn = module.get_function("branch_test")
        assert fn is not None

        cfg = ControlFlowGraph(fn)
        assert len(cfg.nodes) >= 3

        dom = DominatorAnalysis(cfg)
        entry_name = cfg.entry_node.name
        # Entry dominates itself
        assert dom.dominates(entry_name, entry_name)


def test_natural_loop_detection():
    code = """
    int loop_test(int n) {
        int sum = 0;
        for (int i = 0; i < n; i++) {
            sum += i;
        }
        return sum;
    }
    """
    runner = ClangRunner()
    with tempfile.TemporaryDirectory() as td:
        c_path = os.path.join(td, "loop.c")
        ll_path = os.path.join(td, "loop.ll")
        with open(c_path, "w") as f:
            f.write(code)
        runner.compile_to_ir(c_path, ll_path)
        module = IRParser(open(ll_path).read()).parse()
        fn = module.get_function("loop_test")
        assert fn is not None

        cfg = ControlFlowGraph(fn)
        dom = DominatorAnalysis(cfg)
        loops = LoopAnalysis(cfg, dom)
        assert len(loops.loops) == 1
        assert loops.loops[0].header is not None
        assert len(loops.loops[0].body) >= 2
