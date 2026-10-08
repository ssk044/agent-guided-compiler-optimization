"""
Semantic Analyzer for AST validation, type-checking, and variable scoping.
"""
from dataclasses import dataclass, field
from typing import List, Optional
from src.ast.nodes import (
    ASTNode, ProgramNode, FunctionDefNode, ParamNode, VarDeclNode,
    BlockNode, AssignmentNode, BinaryOpNode, UnaryOpNode,
    LiteralNode, VariableNode, IfStmtNode, WhileStmtNode,
    ForStmtNode, ReturnStmtNode, FunctionCallNode, ExprStmtNode, TypeNode
)
from src.ast.visitor import ASTVisitor
from src.semantic.symbol_table import SymbolTable, Symbol


@dataclass
class SemanticDiagnostic:
    severity: str # "ERROR" or "WARNING"
    message: str
    line: int
    column: int

    def __str__(self) -> str:
        return f"[{self.severity}] line {self.line}:{self.column} - {self.message}"


class SemanticAnalyzer(ASTVisitor):
    def __init__(self):
        self.symbol_table = SymbolTable()
        self.diagnostics: List[SemanticDiagnostic] = []
        self.current_function: Optional[FunctionDefNode] = None
        self._all_symbols: List[Symbol] = []

        # Predefine standard runtime library functions like printf
        printf_sym = Symbol(
            name="printf",
            type_node=TypeNode(name="int"),
            is_function=True,
            param_types=[TypeNode(name="char", pointer_level=1)],
            line=0, column=0
        )
        self.symbol_table.define(printf_sym)

    def analyze(self, program: ProgramNode) -> List[SemanticDiagnostic]:
        self.diagnostics = []
        self.visit(program)
        self._check_unused_symbols()
        return self.diagnostics

    def _error(self, message: str, node: ASTNode):
        self.diagnostics.append(SemanticDiagnostic("ERROR", message, node.line, node.column))

    def _warn(self, message: str, node: ASTNode):
        self.diagnostics.append(SemanticDiagnostic("WARNING", message, node.line, node.column))

    def _check_unused_symbols(self):
        for sym in self._all_symbols:
            if not sym.is_function and sym.name != "main" and sym.references == 0:
                self._warn(f"Unused variable '{sym.name}'", ASTNode(line=sym.line, column=sym.column))

    def visit_ProgramNode(self, node: ProgramNode):
        for decl in node.declarations:
            self.visit(decl)

    def visit_FunctionDefNode(self, node: FunctionDefNode):
        func_sym = Symbol(
            name=node.name,
            type_node=node.return_type,
            is_function=True,
            param_types=[p.type_node for p in node.params],
            line=node.line,
            column=node.column
        )
        if not self.symbol_table.define(func_sym):
            self._error(f"Redefinition of function '{node.name}'", node)

        prev_func = self.current_function
        self.current_function = node
        self.symbol_table.enter_scope()

        for param in node.params:
            self.visit(param)

        self.visit(node.body)

        self.symbol_table.exit_scope()
        self.current_function = prev_func

    def visit_ParamNode(self, node: ParamNode):
        sym = Symbol(
            name=node.name,
            type_node=node.type_node,
            line=node.line,
            column=node.column
        )
        if not self.symbol_table.define(sym):
            self._error(f"Redefinition of parameter '{node.name}'", node)
        else:
            self._all_symbols.append(sym)

    def visit_VarDeclNode(self, node: VarDeclNode):
        sym = Symbol(
            name=node.name,
            type_node=node.type_node,
            is_constant=node.type_node.is_const,
            line=node.line,
            column=node.column
        )
        if not self.symbol_table.define(sym):
            self._error(f"Redefinition of variable '{node.name}' in same scope", node)
        else:
            self._all_symbols.append(sym)

        if node.initializer:
            self.visit(node.initializer)

    def visit_BlockNode(self, node: BlockNode):
        self.symbol_table.enter_scope()
        returned = False
        for stmt in node.statements:
            if returned:
                self._warn("Unreachable statement after return", stmt)
            self.visit(stmt)
            if isinstance(stmt, ReturnStmtNode):
                returned = True
        self.symbol_table.exit_scope()

    def visit_AssignmentNode(self, node: AssignmentNode):
        sym = self.symbol_table.lookup(node.target)
        if not sym:
            self._error(f"Assignment to undeclared variable '{node.target}'", node)
        elif sym.is_constant:
            self._error(f"Cannot assign to const variable '{node.target}'", node)
        else:
            self.symbol_table.mark_referenced(node.target)

        if node.value:
            self.visit(node.value)

    def visit_VariableNode(self, node: VariableNode):
        sym = self.symbol_table.lookup(node.name)
        if not sym:
            self._error(f"Use of undeclared variable '{node.name}'", node)
        else:
            self.symbol_table.mark_referenced(node.name)

    def visit_BinaryOpNode(self, node: BinaryOpNode):
        if node.left: self.visit(node.left)
        if node.right: self.visit(node.right)
        # Check for division by zero literal
        if node.op in ("/", "%") and isinstance(node.right, LiteralNode) and node.right.value == 0:
            self._error("Division or modulo by zero", node)

    def visit_UnaryOpNode(self, node: UnaryOpNode):
        if node.operand:
            self.visit(node.operand)

    def visit_IfStmtNode(self, node: IfStmtNode):
        if node.condition: self.visit(node.condition)
        if node.then_branch: self.visit(node.then_branch)
        if node.else_branch: self.visit(node.else_branch)

    def visit_WhileStmtNode(self, node: WhileStmtNode):
        if node.condition: self.visit(node.condition)
        if node.body: self.visit(node.body)

    def visit_ForStmtNode(self, node: ForStmtNode):
        self.symbol_table.enter_scope()
        if node.init: self.visit(node.init)
        if node.condition: self.visit(node.condition)
        if node.update: self.visit(node.update)
        if node.body: self.visit(node.body)
        self.symbol_table.exit_scope()

    def visit_ReturnStmtNode(self, node: ReturnStmtNode):
        if self.current_function:
            func_ret = self.current_function.return_type.name
            if func_ret == "void" and node.value is not None:
                self._error("Void function should not return a value", node)
            elif func_ret != "void" and node.value is None:
                self._warn(f"Non-void function '{self.current_function.name}' should return a value", node)
        if node.value:
            self.visit(node.value)

    def visit_FunctionCallNode(self, node: FunctionCallNode):
        sym = self.symbol_table.lookup(node.name)
        if not sym:
            self._warn(f"Call to undeclared function '{node.name}' (assuming external linkage)", node)
        elif not sym.is_function:
            self._error(f"'{node.name}' is not a function and cannot be called", node)
        for arg in node.args:
            self.visit(arg)

    def visit_ExprStmtNode(self, node: ExprStmtNode):
        if node.expr:
            self.visit(node.expr)
