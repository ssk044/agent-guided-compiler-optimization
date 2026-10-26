"""Readable three-address-code style view of parsed LLVM IR.

LLVM IR remains the executable intermediate representation.  This renderer is
an educational projection used to connect the optimization workflow to the
standard compiler-design TAC syllabus.
"""
from __future__ import annotations

from src.llvm.ir_nodes import IRModule, IRInstruction


class TACRenderer:
    """Render the supported LLVM instructions as beginner-friendly TAC."""

    BINARY_SYMBOLS = {
        "add": "+", "sub": "−", "mul": "×", "sdiv": "÷", "udiv": "÷",
        "srem": "%", "urem": "%", "shl": "<<", "lshr": ">>",
        "ashr": ">> (signed)", "and": "AND", "or": "OR", "xor": "XOR",
    }
    COMPARISON_SYMBOLS = {
        "eq": "==", "ne": "!=", "slt": "<", "ult": "<", "sle": "≤",
        "ule": "≤", "sgt": ">", "ugt": ">", "sge": "≥", "uge": "≥",
    }

    @staticmethod
    def render(module: IRModule, function_name: str = "main") -> str:
        function = module.get_function(function_name)
        if not function:
            return f"# No '{function_name}' function found in this IR module."
        lines: list[str] = [
            f"# Readable three-address code for {function_name}()",
            "# %names are temporary values; labels are places the program can jump to.",
            "",
        ]
        for block in function.blocks:
            lines.append(f"{block.name}:")
            lines.extend(f"  {TACRenderer._instruction(inst)}" for inst in block.instructions)
        return "\n".join(lines)

    @staticmethod
    def _instruction(inst: IRInstruction) -> str:
        operand_values = [operand.value for operand in inst.operands]
        if inst.is_binary_arithmetic() and len(operand_values) >= 2:
            symbol = TACRenderer.BINARY_SYMBOLS.get(inst.opcode, inst.opcode)
            return f"{inst.result or '_'} = {operand_values[0]} {symbol} {operand_values[1]}"
        if inst.opcode == "icmp" and len(operand_values) >= 2:
            predicate = next((m for m in inst.modifiers if m in TACRenderer.COMPARISON_SYMBOLS), None)
            predicate = TACRenderer.COMPARISON_SYMBOLS.get(predicate, "compares with")
            return f"{inst.result or '_'} = {operand_values[0]} {predicate} {operand_values[1]}"
        if inst.opcode == "alloca":
            return f"{inst.result or '_'} = reserve a memory slot"
        if inst.opcode == "load" and operand_values:
            return f"{inst.result or '_'} = read from {operand_values[0]}"
        if inst.opcode == "store" and len(operand_values) >= 2:
            return f"write {operand_values[0]} into {operand_values[1]}"
        if inst.opcode == "getelementptr" and operand_values:
            indexes = ", ".join(operand_values[1:])
            return f"{inst.result or '_'} = address of {operand_values[0]} at indexes [{indexes}]"
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
