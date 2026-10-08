"""
Unit tests for OptimizationAgent and proposal validation.
"""
from src.agent import OptimizationAgent, OptimizationProposal
from src.llvm import IRParser


def test_agent_proposal_generation():
    ir = """
define i32 @calc(i32 %x) {
entry:
  %a = add i32 10, 20
  %b = mul i32 %x, 16
  ret i32 %b
}
"""
    c_source = "int calc(int x) { int a = 10 + 20; return x * 16; }"
    module = IRParser(ir).parse()

    agent = OptimizationAgent()
    proposal = agent.analyze_and_propose(c_source, module, ir)

    assert isinstance(proposal, OptimizationProposal)
    assert len(proposal.recommended_passes) > 0
    assert proposal.safety_assessment != ""
    assert proposal.expected_speedup_estimate >= 1.0
