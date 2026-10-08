"""
Data structures representing LLVM IR Modules, Functions, Basic Blocks, and Instructions.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set


@dataclass
class IROperand:
    type: str # e.g. "i32", "i1", "ptr"
    value: str # e.g. "%1", "42", "true", "@.str"

    def is_constant(self) -> bool:
        if self.value in ("true", "false", "null"):
            return True
        try:
            int(self.value)
            return True
        except ValueError:
            try:
                float(self.value)
                return True
            except ValueError:
                return False

    def get_constant_int(self) -> Optional[int]:
        try:
            return int(self.value)
        except ValueError:
            return None

    def __str__(self) -> str:
        if self.type:
            return f"{self.type} {self.value}"
        return self.value


@dataclass
class IRInstruction:
    opcode: str # "add", "alloca", "load", "store", "br", "ret", "icmp", "mul", etc.
    result: Optional[str] = None # e.g. "%3"
    type: Optional[str] = None # e.g. "i32"
    operands: List[IROperand] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list) # e.g. ["nsw", "nuw", "align 4"]
    raw_text: str = "" # Original or rendered LLVM IR line

    # Metadata/Comments
    comment: str = ""

    def is_terminator(self) -> bool:
        return self.opcode in ("br", "ret", "switch", "indirectbr", "unreachable")

    def is_binary_arithmetic(self) -> bool:
        return self.opcode in (
            "add", "sub", "mul", "sdiv", "udiv", "srem", "urem",
            "shl", "lshr", "ashr", "and", "or", "xor"
        )

    def is_comparison(self) -> bool:
        return self.opcode in ("icmp", "fcmp")

    def is_memory_op(self) -> bool:
        return self.opcode in ("alloca", "load", "store", "getelementptr")

    def is_pure(self) -> bool:
        """Returns True if the instruction has no side-effects and can be safely eliminated if unused."""
        if self.is_terminator() or self.opcode in ("store", "call", "invoke", "fence"):
            return False
        return True

    def get_used_variables(self) -> Set[str]:
        """Returns set of register names read by this instruction."""
        used = set()
        for op in self.operands:
            if op.value.startswith("%") or op.value.startswith("@"):
                used.add(op.value)
        return used

    def replace_variable_use(self, old_var: str, new_val: str, new_type: Optional[str] = None):
        """Replaces uses of old_var with new_val in both operands and raw_text."""
        for op in self.operands:
            if op.value == old_var:
                op.value = new_val
                if new_type:
                    op.type = new_type
        if self.raw_text and old_var in self.raw_text:
            import re
            pattern = rf"(?<![\w%]){re.escape(old_var)}(?!\w)"
            self.raw_text = re.sub(pattern, new_val, self.raw_text)

    def render(self) -> str:
        """Renders instruction as LLVM IR text."""
        if self.raw_text:
            return self.raw_text

        parts = []
        if self.result:
            parts.append(f"{self.result} =")

        parts.append(self.opcode)
        if self.modifiers:
            parts.extend(self.modifiers)

        if self.opcode == "store":
            # store <ty> <val>, <ty>* <ptr>
            val_op = self.operands[0]
            ptr_op = self.operands[1]
            parts.append(f"{val_op.type} {val_op.value}, {ptr_op.type} {ptr_op.value}")
        elif self.opcode == "load":
            # %x = load <ty>, <ty>* <ptr>
            ptr_op = self.operands[0]
            parts.append(f"{self.type}, {ptr_op.type} {ptr_op.value}")
        elif self.opcode == "br":
            if len(self.operands) == 1:
                parts.append(f"label {self.operands[0].value}")
            elif len(self.operands) == 3:
                cond, t_label, f_label = self.operands
                parts.append(f"i1 {cond.value}, label {t_label.value}, label {f_label.value}")
        elif self.opcode == "ret":
            if self.operands:
                parts.append(f"{self.operands[0].type} {self.operands[0].value}")
            else:
                parts.append("void")
        else:
            op_strs = [f"{op.type} {op.value}".strip() for op in self.operands]
            if self.type and not self.result:
                parts.append(self.type)
            parts.append(", ".join(op_strs))

        line = "  " + " ".join(parts)
        if self.comment:
            line += f" ; {self.comment}"
        return line


@dataclass
class IRBasicBlock:
    name: str # e.g. "entry", "for.cond", "12"
    instructions: List[IRInstruction] = field(default_factory=list)
    predecessors: Set[str] = field(default_factory=set)
    successors: Set[str] = field(default_factory=set)

    def add_instruction(self, inst: IRInstruction):
        self.instructions.append(inst)

    def remove_instruction(self, inst: IRInstruction):
        if inst in self.instructions:
            self.instructions.remove(inst)

    def get_terminator(self) -> Optional[IRInstruction]:
        if self.instructions and self.instructions[-1].is_terminator():
            return self.instructions[-1]
        return None

    def render(self) -> List[str]:
        lines = []
        if self.name and not self.name.isdigit():
            lines.append(f"{self.name}:")
        elif self.name and self.name.isdigit():
            lines.append(f"; <label>:{self.name}:")
        for inst in self.instructions:
            lines.append(inst.render())
        return lines


@dataclass
class IRFunction:
    name: str
    return_type: str = "i32"
    arguments: List[IROperand] = field(default_factory=list)
    blocks: List[IRBasicBlock] = field(default_factory=list)
    attributes: List[str] = field(default_factory=list)
    is_declaration: bool = False
    raw_header: str = ""

    def get_block(self, name: str) -> Optional[IRBasicBlock]:
        for b in self.blocks:
            if b.name == name:
                return b
        return None

    @property
    def entry_block(self) -> Optional[IRBasicBlock]:
        return self.blocks[0] if self.blocks else None

    @property
    def total_instructions(self) -> int:
        return sum(len(b.instructions) for b in self.blocks)

    def render(self) -> List[str]:
        lines = []
        if self.is_declaration:
            if self.raw_header:
                lines.append(self.raw_header)
            else:
                args_str = ", ".join(f"{arg.type} {arg.value}".strip() for arg in self.arguments)
                lines.append(f"declare {self.return_type} @{self.name}({args_str})")
            return lines

        if self.raw_header:
            lines.append(self.raw_header)
        else:
            args_str = ", ".join(f"{arg.type} {arg.value}".strip() for arg in self.arguments)
            attr_str = " " + " ".join(self.attributes) if self.attributes else ""
            lines.append(f"define {self.return_type} @{self.name}({args_str}){attr_str} {{")

        for b in self.blocks:
            lines.extend(b.render())

        lines.append("}")
        return lines


@dataclass
class IRModule:
    source_filename: str = ""
    target_datalayout: str = ""
    target_triple: str = ""
    global_vars: List[str] = field(default_factory=list)
    functions: List[IRFunction] = field(default_factory=list)
    metadata_lines: List[str] = field(default_factory=list)
    raw_header_lines: List[str] = field(default_factory=list)

    def get_function(self, name: str) -> Optional[IRFunction]:
        for f in self.functions:
            if f.name == name or f.name == f"@{name}":
                return f
        return None

    @property
    def total_instructions(self) -> int:
        return sum(f.total_instructions for f in self.functions if not f.is_declaration)

    def render(self) -> str:
        lines = []
        if self.raw_header_lines:
            lines.extend(self.raw_header_lines)
        else:
            if self.source_filename:
                lines.append(f'source_filename = "{self.source_filename}"')
            if self.target_datalayout:
                lines.append(f'target datalayout = "{self.target_datalayout}"')
            if self.target_triple:
                lines.append(f'target triple = "{self.target_triple}"')
            lines.append("")

        for g in self.global_vars:
            lines.append(g)
        if self.global_vars:
            lines.append("")

        for f in self.functions:
            lines.extend(f.render())
            lines.append("")

        for m in self.metadata_lines:
            lines.append(m)

        return "\n".join(lines)
