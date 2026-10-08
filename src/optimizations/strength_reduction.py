"""
Strength Reduction and Algebraic Simplification Optimization Pass.
Converts costly operations into cheaper equivalents (e.g. mul by power of 2 to shift, identity reductions).
"""
import math
import re
from typing import Optional, Tuple
from src.optimizations.base import OptimizationPass, PassResult
from src.llvm.ir_nodes import IRModule, IRFunction, IRInstruction, IROperand


class StrengthReductionPass(OptimizationPass):
    def __init__(self):
        super().__init__("StrengthReduction")

    def run(self, module: IRModule) -> PassResult:
        changes = 0
        details = []

        for func in module.functions:
            if func.is_declaration:
                continue

            for block in func.blocks:
                to_remove = []
                for inst in block.instructions:
                    if not inst.is_binary_arithmetic() or not inst.result:
                        continue
                    if len(inst.operands) < 2:
                        continue

                    reduced = self._try_reduce_strength(inst)
                    if reduced:
                        action, target_val, new_ty = reduced
                        changes += 1
                        if action == "replace_with_val":
                            details.append(f"Algebraic simplification: {inst.result} = {inst.opcode} -> {target_val}")
                            self._substitute_everywhere(func, inst.result, target_val)
                            to_remove.append(inst)
                        elif action == "transform_inst":
                            # Modified in-place (e.g. mul -> shl)
                            details.append(f"Strength reduction: {inst.result} converted to {inst.opcode}")

                for inst in to_remove:
                    block.remove_instruction(inst)

        return PassResult(
            pass_name=self.name,
            changes_made=changes,
            description=f"Applied {changes} strength reduction/simplification(s)",
            details=details
        )

    def _try_reduce_strength(self, inst: IRInstruction) -> Optional[Tuple[str, str, str]]:
        op = inst.opcode
        op1 = inst.operands[0]
        op2 = inst.operands[1]
        c1 = op1.get_constant_int()
        c2 = op2.get_constant_int()
        ty = op1.type or "i32"

        # 1. Identity and zero properties
        # x * 0 = 0 or 0 * x = 0
        if op == "mul" and (c1 == 0 or c2 == 0):
            return ("replace_with_val", "0", ty)

        # x * 1 = x
        if op == "mul":
            if c2 == 1:
                return ("replace_with_val", op1.value, ty)
            elif c1 == 1:
                return ("replace_with_val", op2.value, ty)

        # x + 0 = x
        if op == "add":
            if c2 == 0:
                return ("replace_with_val", op1.value, ty)
            elif c1 == 0:
                return ("replace_with_val", op2.value, ty)

        # x - 0 = x
        if op == "sub" and c2 == 0:
            return ("replace_with_val", op1.value, ty)

        # x - x = 0 or x ^ x = 0
        if (op in ("sub", "xor")) and op1.value == op2.value:
            return ("replace_with_val", "0", ty)

        # x & 0 = 0
        if op == "and" and (c1 == 0 or c2 == 0):
            return ("replace_with_val", "0", ty)

        # x | 0 = x
        if op == "or":
            if c2 == 0:
                return ("replace_with_val", op1.value, ty)
            elif c1 == 0:
                return ("replace_with_val", op2.value, ty)

        # 2. Strength Reduction: mul by power of 2 -> shl
        if op == "mul":
            shift_amt = None
            var_val = None
            if c2 is not None and c2 > 0 and (c2 & (c2 - 1)) == 0:
                shift_amt = int(math.log2(c2))
                var_val = op1.value
            elif c1 is not None and c1 > 0 and (c1 & (c1 - 1)) == 0:
                shift_amt = int(math.log2(c1))
                var_val = op2.value

            if shift_amt is not None and shift_amt > 0:
                inst.opcode = "shl"
                inst.operands = [
                    IROperand(type=ty, value=var_val),
                    IROperand(type=ty, value=str(shift_amt))
                ]
                inst.raw_text = f"  {inst.result} = shl {ty} {var_val}, {shift_amt}"
                return ("transform_inst", "", ty)

        # 3. Strength Reduction: sdiv by power of 2 -> ashr
        if op in ("sdiv", "udiv") and c2 is not None and c2 > 0 and (c2 & (c2 - 1)) == 0:
            shift_amt = int(math.log2(c2))
            if shift_amt > 0:
                inst.opcode = "ashr"
                inst.operands = [
                    IROperand(type=ty, value=op1.value),
                    IROperand(type=ty, value=str(shift_amt))
                ]
                inst.raw_text = f"  {inst.result} = ashr {ty} {op1.value}, {shift_amt}"
                return ("transform_inst", "", ty)

        return None

    def _substitute_everywhere(self, func: IRFunction, old_reg: str, new_val: str):
        for block in func.blocks:
            for inst in block.instructions:
                inst.replace_variable_use(old_reg, new_val)
