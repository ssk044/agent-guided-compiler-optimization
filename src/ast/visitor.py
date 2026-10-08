"""
AST Visitor pattern and Pretty Printer for AST nodes.
"""
from typing import Any
from src.ast.nodes import (
    ASTNode, ProgramNode, FunctionDefNode, ParamNode, VarDeclNode,
    BlockNode, AssignmentNode, BinaryOpNode, UnaryOpNode,
    LiteralNode, VariableNode, IfStmtNode, WhileStmtNode,
    ForStmtNode, ReturnStmtNode, FunctionCallNode, ExprStmtNode
)


class ASTVisitor:
    """Base visitor pattern for traversing AST nodes."""
    def visit(self, node: ASTNode) -> Any:
        method_name = f"visit_{node.__class__.__name__}"
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: ASTNode) -> Any:
        for attr, value in vars(node).items():
            if isinstance(value, ASTNode):
                self.visit(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, ASTNode):
                        self.visit(item)


class ASTPrinter(ASTVisitor):
    """Generates a clean hierarchical ASCII/Unicode tree string of the AST."""
    def __init__(self):
        self.lines = []

    def print_tree(self, node: ASTNode) -> str:
        self.lines = []
        self._format_node(node, "", True)
        return "\n".join(self.lines)

    def _format_node(self, node: ASTNode, prefix: str, is_tail: bool):
        branch = "└── " if is_tail else "├── "
        node_repr = self._get_label(node)
        self.lines.append(f"{prefix}{branch}{node_repr}")

        child_prefix = prefix + ("    " if is_tail else "│   ")
        children = self._get_children(node)
        for i, child in enumerate(children):
            self._format_node(child, child_prefix, i == len(children) - 1)

    def _get_label(self, node: ASTNode) -> str:
        if isinstance(node, ProgramNode):
            return "Program"
        elif isinstance(node, FunctionDefNode):
            return f"FunctionDef: {node.return_type} {node.name}()"
        elif isinstance(node, ParamNode):
            return f"Param: {node.type_node} {node.name}"
        elif isinstance(node, VarDeclNode):
            return f"VarDecl: {node.type_node} {node.name}"
        elif isinstance(node, BlockNode):
            return "Block"
        elif isinstance(node, AssignmentNode):
            return f"Assign: {node.target} {node.op}"
        elif isinstance(node, BinaryOpNode):
            return f"BinaryOp: '{node.op}'"
        elif isinstance(node, UnaryOpNode):
            pos = "pre" if node.is_prefix else "post"
            return f"UnaryOp: {node.op} ({pos})"
        elif isinstance(node, LiteralNode):
            return f"Literal: {node.value} ({node.lit_type})"
        elif isinstance(node, VariableNode):
            return f"Var: {node.name}"
        elif isinstance(node, IfStmtNode):
            return "IfStmt"
        elif isinstance(node, WhileStmtNode):
            return "WhileStmt"
        elif isinstance(node, ForStmtNode):
            return "ForStmt"
        elif isinstance(node, ReturnStmtNode):
            return "Return"
        elif isinstance(node, FunctionCallNode):
            return f"Call: {node.name}()"
        elif isinstance(node, ExprStmtNode):
            return "ExprStmt"
        return node.__class__.__name__

    def _get_children(self, node: ASTNode) -> list:
        children = []
        if isinstance(node, ProgramNode):
            children.extend(node.declarations)
        elif isinstance(node, FunctionDefNode):
            children.extend(node.params)
            children.append(node.body)
        elif isinstance(node, VarDeclNode):
            if node.initializer:
                children.append(node.initializer)
        elif isinstance(node, BlockNode):
            children.extend(node.statements)
        elif isinstance(node, AssignmentNode):
            if node.value:
                children.append(node.value)
        elif isinstance(node, BinaryOpNode):
            if node.left: children.append(node.left)
            if node.right: children.append(node.right)
        elif isinstance(node, UnaryOpNode):
            if node.operand: children.append(node.operand)
        elif isinstance(node, IfStmtNode):
            if node.condition: children.append(node.condition)
            if node.then_branch: children.append(node.then_branch)
            if node.else_branch: children.append(node.else_branch)
        elif isinstance(node, WhileStmtNode):
            if node.condition: children.append(node.condition)
            if node.body: children.append(node.body)
        elif isinstance(node, ForStmtNode):
            if node.init: children.append(node.init)
            if node.condition: children.append(node.condition)
            if node.update: children.append(node.update)
            if node.body: children.append(node.body)
        elif isinstance(node, ReturnStmtNode):
            if node.value: children.append(node.value)
        elif isinstance(node, FunctionCallNode):
            children.extend(node.args)
        elif isinstance(node, ExprStmtNode):
            if node.expr: children.append(node.expr)
        return children
