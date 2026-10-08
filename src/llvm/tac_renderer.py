"""Readable three-address-code style view of parsed LLVM IR.

LLVM IR remains the executable intermediate representation.  This renderer is
an educational projection used to connect the optimization workflow to the
standard compiler-design TAC syllabus.
"""
from __future__ import annotations

from src.llvm.ir_nodes import IRModule, IRInstruction


class TACRenderer:
    @staticmethod
    def render(module: IRModule, function_name: str = "main") -> str:
        function = module.get_function(function_name)
        if not function:
            return "# No main function found"
        lines: list[str] = [f"# TAC-style view: {function_name}"]
        for block in function.blocks:
            lines.append(f"{block.name}:")
            lines.extend(f"  {TACRenderer._instruction(inst)}" for inst in block.instructions)
        return "\n".join(lines)

    @staticmethod
    def _instruction(inst: IRInstruction) -> str:
        operand_values = [operand.value for operand in inst.operands]
        if inst.is_binary_arithmetic() and len(operand_values) >= 2:
            return f"{inst.result or '_'} = {operand_values[0]} {inst.opcode} {operand_values[1]}"
        if inst.opcode == "icmp" and len(operand_values) >= 2:
            predicate = next((m for m in inst.modifiers if m in {"eq", "ne", "slt", "sle", "sgt", "sge"}), "compare")
            return f"{inst.result or '_'} = {operand_values[0]} {predicate} {operand_values[1]}"
        if inst.opcode == "load" and operand_values:
            return f"{inst.result or '_'} = load {operand_values[0]}"
        if inst.opcode == "store" and len(operand_values) >= 2:
            return f"store {operand_values[0]} -> {operand_values[1]}"
        if inst.opcode == "br":
            if len(operand_values) == 1:
                return f"goto {operand_values[0]}"
            if len(operand_values) == 3:
                return f"if {operand_values[0]} goto {operand_values[1]} else goto {operand_values[2]}"
        if inst.opcode == "ret":
            return f"return {operand_values[0] if operand_values else ''}".strip()
        if inst.opcode == "call":
            # render() already includes the result assignment when one exists.
            return inst.render().strip()
        return inst.render().strip()
