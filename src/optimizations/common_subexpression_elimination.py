"""
Common Subexpression Elimination (CSE) Optimization Pass.
Identifies and eliminates redundant identical computations across basic blocks.
"""
import re
from typing import Dict, Tuple, Optional
from src.optimizations.base import OptimizationPass, PassResult
from src.llvm.ir_nodes import IRModule, IRFunction, IRInstruction
from src.analysis.cfg import ControlFlowGraph
from src.analysis.dominators import DominatorAnalysis


class CommonSubexpressionEliminationPass(OptimizationPass):
    def __init__(self):
        super().__init__("CommonSubexpressionElimination")

    def run(self, module: IRModule) -> PassResult:
        changes = 0
        details = []

        for func in module.functions:
            if func.is_declaration:
                continue

            cfg = ControlFlowGraph(func)
            dom = DominatorAnalysis(cfg)

            # Map from expr_key -> (result_reg, defining_block_name)
            seen_exprs: Dict[Tuple, Tuple[str, str]] = {}

            for block in func.blocks:
                to_remove = []
                for inst in block.instructions:
                    if not inst.is_binary_arithmetic() or not inst.result:
                        continue

                    if len(inst.operands) < 2:
                        continue

                    op1 = inst.operands[0].value
                    op2 = inst.operands[1].value
                    opcode = inst.opcode
                    ty = inst.operands[0].type or "i32"

                    # Commutative canonicalization
                    if opcode in ("add", "mul", "and", "or", "xor"):
                        operands_key = tuple(sorted([op1, op2]))
                    else:
                        operands_key = (op1, op2)

                    expr_key = (opcode, ty, operands_key)

                    if expr_key in seen_exprs:
                        earlier_res, earlier_block = seen_exprs[expr_key]
                        # Verify that the earlier definition dominates the current block
                        if dom.dominates(earlier_block, block.name):
                            # Redundant expression!
                            changes += 1
                            details.append(f"Eliminated duplicate {inst.result} = {opcode} (reusing {earlier_res})")
                            self._substitute_everywhere(func, inst.result, earlier_res)
                            to_remove.append(inst)
                            continue

                    # First time seeing this expr
                    seen_exprs[expr_key] = (inst.result, block.name)

                for inst in to_remove:
                    block.remove_instruction(inst)

        return PassResult(
            pass_name=self.name,
            changes_made=changes,
            description=f"Eliminated {changes} common subexpression(s)",
            details=details
        )

    def _substitute_everywhere(self, func: IRFunction, old_reg: str, new_val: str):
        for block in func.blocks:
            for inst in block.instructions:
                inst.replace_variable_use(old_reg, new_val)
