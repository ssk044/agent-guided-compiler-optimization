"""
Constant Folding Optimization Pass.
Evaluates expressions with known constant operands at compile-time.
"""
from typing import Optional, Tuple
from src.optimizations.base import OptimizationPass, PassResult
from src.llvm.ir_nodes import IRModule, IRFunction, IRInstruction, IROperand


class ConstantFoldingPass(OptimizationPass):
    def __init__(self):
        super().__init__("ConstantFolding")

    def run(self, module: IRModule) -> PassResult:
        changes = 0
        details = []

        for func in module.functions:
            if func.is_declaration:
                continue

            for block in func.blocks:
                to_remove = []
                for inst in block.instructions:
                    folded_val, folded_ty = self._try_fold_instruction(inst)
                    if folded_val is not None and inst.result:
                        # Propagate this folded constant to all uses in the function
                        changes += 1
                        val_str = str(folded_val)
                        details.append(f"Folded {inst.result} = {inst.opcode} -> {val_str} ({folded_ty})")
                        self._substitute_everywhere(func, inst.result, val_str, folded_ty)
                        to_remove.append(inst)

                for inst in to_remove:
                    block.remove_instruction(inst)

        return PassResult(
            pass_name=self.name,
            changes_made=changes,
            description=f"Folded {changes} constant expression(s)",
            details=details
        )

    def _try_fold_instruction(self, inst: IRInstruction) -> Tuple[Optional[int], Optional[str]]:
        if not inst.is_binary_arithmetic() and not inst.is_comparison():
            return None, None

        if len(inst.operands) < 2:
            return None, None

        c1 = inst.operands[0].get_constant_int()
        c2 = inst.operands[1].get_constant_int()

        if c1 is None or c2 is None:
            return None, None

        ty = inst.operands[0].type or "i32"
        op = inst.opcode

        res = None
        if op == "add":
            res = c1 + c2
        elif op == "sub":
            res = c1 - c2
        elif op == "mul":
            res = c1 * c2
        elif op in ("sdiv", "udiv"):
            if c2 != 0:
                res = c1 // c2
        elif op in ("srem", "urem"):
            if c2 != 0:
                res = c1 % c2
        elif op == "shl":
            if 0 <= c2 < 32:
                res = c1 << c2
        elif op in ("ashr", "lshr"):
            if 0 <= c2 < 32:
                res = c1 >> c2
        elif op == "and":
            res = c1 & c2
        elif op == "or":
            res = c1 | c2
        elif op == "xor":
            res = c1 ^ c2
        elif op == "icmp":
            # Determine predicate from modifiers or raw_text
            pred = "eq"
            for m in ("eq", "ne", "ugt", "uge", "ult", "ule", "sgt", "sge", "slt", "sle"):
                if m in inst.modifiers or m in inst.raw_text:
                    pred = m
                    break
            ty = "i1"
            if pred == "eq": res = 1 if c1 == c2 else 0
            elif pred == "ne": res = 1 if c1 != c2 else 0
            elif pred in ("sgt", "ugt"): res = 1 if c1 > c2 else 0
            elif pred in ("sge", "uge"): res = 1 if c1 >= c2 else 0
            elif pred in ("slt", "ult"): res = 1 if c1 < c2 else 0
            elif pred in ("sle", "ule"): res = 1 if c1 <= c2 else 0

        return res, ty

    def _substitute_everywhere(self, func: IRFunction, old_reg: str, new_val: str, new_type: str):
        for block in func.blocks:
            for inst in block.instructions:
                inst.replace_variable_use(old_reg, new_val, new_type)
