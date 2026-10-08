"""
Unit tests for individual optimization passes.
"""
from src.llvm import IRParser, IREmitter
from src.optimizations import (
    PassManager, ConstantFoldingPass, ConstantPropagationPass,
    DeadCodeEliminationPass, CommonSubexpressionEliminationPass,
    StrengthReductionPass
)


def test_constant_folding():
    ir = """
define i32 @test() {
entry:
  %res = add i32 10, 25
  ret i32 %res
}
"""
    module = IRParser(ir).parse()
    cf = ConstantFoldingPass()
    res = cf.run(module)
    assert res.changes_made == 1
    rendered = module.render()
    assert "35" in rendered


def test_strength_reduction():
    ir = """
define i32 @test(i32 %x) {
entry:
  %res = mul i32 %x, 8
  ret i32 %res
}
"""
    module = IRParser(ir).parse()
    sr = StrengthReductionPass()
    res = sr.run(module)
    assert res.changes_made == 1
    rendered = module.render()
    assert "shl" in rendered and "3" in rendered


def test_common_subexpression_elimination():
    ir = """
define i32 @test(i32 %x, i32 %y) {
entry:
  %t1 = add i32 %x, %y
  %t2 = add i32 %x, %y
  %res = mul i32 %t1, %t2
  ret i32 %res
}
"""
    module = IRParser(ir).parse()
    cse = CommonSubexpressionEliminationPass()
    res = cse.run(module)
    assert res.changes_made == 1
