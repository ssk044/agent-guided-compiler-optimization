"""
Abstract Syntax Tree (AST) node representations.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Any


@dataclass
class ASTNode:
    line: int = 0
    column: int = 0


@dataclass
class TypeNode(ASTNode):
    name: str = "int"
    is_const: bool = False
    pointer_level: int = 0

    def __str__(self) -> str:
        const_prefix = "const " if self.is_const else ""
        ptr_suffix = "*" * self.pointer_level
        return f"{const_prefix}{self.name}{ptr_suffix}"


@dataclass
class ParamNode(ASTNode):
    type_node: TypeNode = field(default_factory=TypeNode)
    name: str = ""


@dataclass
class VarDeclNode(ASTNode):
    type_node: TypeNode = field(default_factory=TypeNode)
    name: str = ""
    initializer: Optional[ASTNode] = None


@dataclass
class BlockNode(ASTNode):
    statements: List[ASTNode] = field(default_factory=list)


@dataclass
class FunctionDefNode(ASTNode):
    return_type: TypeNode = field(default_factory=TypeNode)
    name: str = ""
    params: List[ParamNode] = field(default_factory=list)
    body: BlockNode = field(default_factory=BlockNode)


@dataclass
class ProgramNode(ASTNode):
    declarations: List[ASTNode] = field(default_factory=list)


@dataclass
class AssignmentNode(ASTNode):
    target: str = ""
    op: str = "="
    value: Optional[ASTNode] = None


@dataclass
class BinaryOpNode(ASTNode):
    left: Optional[ASTNode] = None
    op: str = "+"
    right: Optional[ASTNode] = None


@dataclass
class UnaryOpNode(ASTNode):
    op: str = "-"
    operand: Optional[ASTNode] = None
    is_prefix: bool = True


@dataclass
class LiteralNode(ASTNode):
    value: Any = 0
    lit_type: str = "int"


@dataclass
class VariableNode(ASTNode):
    name: str = ""


@dataclass
class IfStmtNode(ASTNode):
    condition: Optional[ASTNode] = None
    then_branch: Optional[ASTNode] = None
    else_branch: Optional[ASTNode] = None


@dataclass
class WhileStmtNode(ASTNode):
    condition: Optional[ASTNode] = None
    body: Optional[ASTNode] = None


@dataclass
class ForStmtNode(ASTNode):
    init: Optional[ASTNode] = None
    condition: Optional[ASTNode] = None
    update: Optional[ASTNode] = None
    body: Optional[ASTNode] = None


@dataclass
class ReturnStmtNode(ASTNode):
    value: Optional[ASTNode] = None


@dataclass
class FunctionCallNode(ASTNode):
    name: str = ""
    args: List[ASTNode] = field(default_factory=list)


@dataclass
class ExprStmtNode(ASTNode):
    expr: Optional[ASTNode] = None
