"""
Natural Loop detection and Loop Invariance analysis.
"""
from dataclasses import dataclass, field
from typing import List, Set, Dict, Optional
from src.analysis.cfg import ControlFlowGraph
from src.analysis.dominators import DominatorAnalysis
from src.llvm.ir_nodes import IRInstruction, IRBasicBlock


@dataclass
class NaturalLoop:
    header: str
    latch: str
    body: Set[str] = field(default_factory=set)
    exits: Set[str] = field(default_factory=set)
    preheader: Optional[str] = None


class LoopAnalysis:
    def __init__(self, cfg: ControlFlowGraph, dom: DominatorAnalysis):
        self.cfg = cfg
        self.dom = dom
        self.loops: List[NaturalLoop] = []
        self._find_loops()

    def _find_loops(self):
        # A back-edge is an edge A -> B where B dominates A
        for a_name, a_node in self.cfg.nodes.items():
            for b_name in a_node.successors:
                if self.dom.dominates(b_name, a_name):
                    # Found back-edge a -> b. b is header, a is latch.
                    loop = self._construct_natural_loop(b_name, a_name)
                    self.loops.append(loop)

    def _construct_natural_loop(self, header: str, latch: str) -> NaturalLoop:
        body: Set[str] = {header, latch}
        stack = [latch]

        while stack:
            m = stack.pop()
            m_node = self.cfg.nodes.get(m)
            if not m_node:
                continue
            for p in m_node.predecessors:
                if p not in body:
                    body.add(p)
                    stack.append(p)

        # Identify loop exits
        exits: Set[str] = set()
        for b in body:
            node = self.cfg.nodes.get(b)
            if node:
                for succ in node.successors:
                    if succ not in body:
                        exits.add(succ)

        # Identify preheader (a predecessor of header that is outside the loop)
        preheader = None
        header_node = self.cfg.nodes.get(header)
        if header_node:
            outside_preds = [p for p in header_node.predecessors if p not in body]
            if len(outside_preds) == 1:
                preheader = outside_preds[0]

        return NaturalLoop(
            header=header,
            latch=latch,
            body=body,
            exits=exits,
            preheader=preheader
        )

    def find_loop_invariants(self, loop: NaturalLoop) -> List[IRInstruction]:
        """
        Finds instructions inside the loop body whose operands are invariant
        (defined outside the loop or constant).
        """
        invariants: List[IRInstruction] = []
        loop_defined_vars: Set[str] = set()

        for b_name in loop.body:
            node = self.cfg.nodes.get(b_name)
            if node:
                for inst in node.block.instructions:
                    if inst.result:
                        loop_defined_vars.add(inst.result)

        for b_name in loop.body:
            node = self.cfg.nodes.get(b_name)
            if node:
                for inst in node.block.instructions:
                    # Pure instructions only
                    if inst.is_pure() and inst.is_binary_arithmetic() and inst.result:
                        # Check if all operands are either constant or defined outside the loop
                        operands_invariant = True
                        for op in inst.operands:
                            if not op.is_constant():
                                if op.value in loop_defined_vars:
                                    operands_invariant = False
                                    break
                        if operands_invariant:
                            invariants.append(inst)

        return invariants
