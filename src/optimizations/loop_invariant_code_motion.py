"""
Loop-Invariant Code Motion (LICM) Optimization Pass.
Hoists computations that do not vary across loop iterations out into the loop preheader.
"""
from typing import List
from src.optimizations.base import OptimizationPass, PassResult
from src.llvm.ir_nodes import IRModule, IRFunction, IRInstruction
from src.analysis.cfg import ControlFlowGraph
from src.analysis.dominators import DominatorAnalysis
from src.analysis.loop_analysis import LoopAnalysis


class LoopInvariantCodeMotionPass(OptimizationPass):
    def __init__(self):
        super().__init__("LoopInvariantCodeMotion")

    def run(self, module: IRModule) -> PassResult:
        changes = 0
        details = []

        for func in module.functions:
            if func.is_declaration:
                continue

            cfg = ControlFlowGraph(func)
            dom = DominatorAnalysis(cfg)
            loop_analysis = LoopAnalysis(cfg, dom)

            for loop in loop_analysis.loops:
                if not loop.preheader:
                    continue

                preheader_block = func.get_block(loop.preheader)
                if not preheader_block:
                    continue

                invariants = loop_analysis.find_loop_invariants(loop)
                for inv_inst in invariants:
                    # Find which block contains inv_inst
                    containing_block = None
                    for b_name in loop.body:
                        b = func.get_block(b_name)
                        if b and inv_inst in b.instructions:
                            containing_block = b
                            break

                    if not containing_block:
                        continue

                    # Hoist inv_inst into preheader before its terminator
                    containing_block.remove_instruction(inv_inst)
                    if preheader_block.instructions and preheader_block.instructions[-1].is_terminator():
                        preheader_block.instructions.insert(-1, inv_inst)
                    else:
                        preheader_block.instructions.append(inv_inst)

                    changes += 1
                    details.append(
                        f"Hoisted invariant {inv_inst.result} = {inv_inst.opcode} "
                        f"from [{containing_block.name}] to preheader [{preheader_block.name}]"
                    )

        return PassResult(
            pass_name=self.name,
            changes_made=changes,
            description=f"Hoisted {changes} loop-invariant computation(s)",
            details=details
        )
