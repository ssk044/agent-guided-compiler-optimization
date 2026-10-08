"""
Recursive-descent Parser for C subset.
"""
from typing import List, Optional
from src.lexer.tokens import Token, TokenType
from src.ast.nodes import (
    ASTNode, TypeNode, ParamNode, VarDeclNode, BlockNode,
    FunctionDefNode, ProgramNode, AssignmentNode, BinaryOpNode,
    UnaryOpNode, LiteralNode, VariableNode, IfStmtNode,
    WhileStmtNode, ForStmtNode, ReturnStmtNode, FunctionCallNode,
    ExprStmtNode
)


class ParserError(Exception):
    def __init__(self, message: str, token: Token):
        super().__init__(f"Parser error at line {token.line}, col {token.column}: {message} (found {token.type.name} '{token.value}')")
        self.token = token


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def _peek(self, offset: int = 0) -> Token:
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1] # EOF

    def _advance(self) -> Token:
        tok = self._peek()
        if tok.type != TokenType.EOF:
            self.pos += 1
        return tok

    def _check(self, *expected_types: TokenType) -> bool:
        return self._peek().type in expected_types

    def _match(self, *expected_types: TokenType) -> bool:
        if self._check(*expected_types):
            self._advance()
            return True
        return False

    def _consume(self, expected_type: TokenType, err_msg: str) -> Token:
        if self._check(expected_type):
            return self._advance()
        raise ParserError(err_msg, self._peek())

    def parse(self) -> ProgramNode:
        declarations: List[ASTNode] = []
        while not self._check(TokenType.EOF):
            decl = self._parse_top_level()
            if decl:
                declarations.append(decl)
        return ProgramNode(declarations=declarations)

    def _parse_type(self) -> TypeNode:
        is_const = False
        if self._match(TokenType.KW_CONST):
            is_const = True

        type_tok = self._peek()
        type_names = {
            TokenType.KW_INT: "int",
            TokenType.KW_FLOAT: "float",
            TokenType.KW_DOUBLE: "double",
            TokenType.KW_CHAR: "char",
            TokenType.KW_VOID: "void",
        }
        if type_tok.type in type_names:
            self._advance()
            name = type_names[type_tok.type]
        elif type_tok.type == TokenType.IDENTIFIER:
            self._advance()
            name = str(type_tok.value)
        else:
            raise ParserError(f"Expected type specifier, got {type_tok.value}", type_tok)

        ptr_level = 0
        while self._match(TokenType.STAR):
            ptr_level += 1

        return TypeNode(
            line=type_tok.line,
            column=type_tok.column,
            name=name,
            is_const=is_const,
            pointer_level=ptr_level
        )

    def _is_type_start(self) -> bool:
        return self._check(
            TokenType.KW_INT, TokenType.KW_FLOAT, TokenType.KW_DOUBLE,
            TokenType.KW_CHAR, TokenType.KW_VOID, TokenType.KW_CONST
        )

    def _parse_top_level(self) -> ASTNode:
        type_node = self._parse_type()
        name_tok = self._consume(TokenType.IDENTIFIER, "Expected identifier after type")
        
        # Check if function definition
        if self._check(TokenType.LPAREN):
            return self._parse_function_def(type_node, name_tok.value, name_tok.line, name_tok.column)
        
        # Otherwise top-level variable declaration
        init = None
        if self._match(TokenType.ASSIGN):
            init = self._parse_expression()
        self._consume(TokenType.SEMICOLON, "Expected ';' after variable declaration")
        return VarDeclNode(
            line=name_tok.line, column=name_tok.column,
            type_node=type_node, name=name_tok.value, initializer=init
        )

    def _parse_function_def(self, return_type: TypeNode, name: str, line: int, col: int) -> FunctionDefNode:
        self._consume(TokenType.LPAREN, "Expected '(' in function parameter list")
        params: List[ParamNode] = []
        if not self._check(TokenType.RPAREN):
            while True:
                if self._check(TokenType.KW_VOID) and self._peek(1).type == TokenType.RPAREN:
                    self._advance()
                    break
                p_type = self._parse_type()
                p_name_tok = self._consume(TokenType.IDENTIFIER, "Expected parameter name")
                while self._match(TokenType.LBRACKET):
                    if not self._check(TokenType.RBRACKET):
                        self._parse_expression()
                    self._consume(TokenType.RBRACKET, "Expected ']'")
                    p_type.pointer_level += 1
                params.append(ParamNode(line=p_name_tok.line, column=p_name_tok.column, type_node=p_type, name=p_name_tok.value))
                if not self._match(TokenType.COMMA):
                    break
        self._consume(TokenType.RPAREN, "Expected ')' after function parameters")
        body = self._parse_block()
        return FunctionDefNode(line=line, column=col, return_type=return_type, name=name, params=params, body=body)

    def _parse_block(self) -> BlockNode:
        start_tok = self._consume(TokenType.LBRACE, "Expected '{' to start block")
        stmts: List[ASTNode] = []
        while not self._check(TokenType.RBRACE, TokenType.EOF):
            s = self._parse_statement()
            if s:
                stmts.append(s)
        self._consume(TokenType.RBRACE, "Expected '}' to close block")
        return BlockNode(line=start_tok.line, column=start_tok.column, statements=stmts)

    def _parse_statement(self) -> ASTNode:
        tok = self._peek()

        if tok.type == TokenType.LBRACE:
            return self._parse_block()
        elif tok.type == TokenType.KW_IF:
            return self._parse_if_stmt()
        elif tok.type == TokenType.KW_WHILE:
            return self._parse_while_stmt()
        elif tok.type == TokenType.KW_FOR:
            return self._parse_for_stmt()
        elif tok.type == TokenType.KW_RETURN:
            return self._parse_return_stmt()
        elif self._is_type_start():
            return self._parse_var_decl()
        else:
            expr = self._parse_expression()
            self._consume(TokenType.SEMICOLON, "Expected ';' after expression statement")
            return ExprStmtNode(line=tok.line, column=tok.column, expr=expr)

    def _parse_var_decl(self) -> VarDeclNode:
        type_node = self._parse_type()
        name_tok = self._consume(TokenType.IDENTIFIER, "Expected variable name")
        while self._match(TokenType.LBRACKET):
            if not self._check(TokenType.RBRACKET):
                self._parse_expression()
            self._consume(TokenType.RBRACKET, "Expected ']'")
            type_node.pointer_level += 1
        init = None
        if self._match(TokenType.ASSIGN):
            init = self._parse_expression()
        self._consume(TokenType.SEMICOLON, "Expected ';' after variable declaration")
        return VarDeclNode(
            line=name_tok.line, column=name_tok.column,
            type_node=type_node, name=name_tok.value, initializer=init
        )

    def _parse_if_stmt(self) -> IfStmtNode:
        if_tok = self._consume(TokenType.KW_IF, "Expected 'if'")
        self._consume(TokenType.LPAREN, "Expected '(' after 'if'")
        cond = self._parse_expression()
        self._consume(TokenType.RPAREN, "Expected ')' after if condition")
        then_branch = self._parse_statement()
        else_branch = None
        if self._match(TokenType.KW_ELSE):
            else_branch = self._parse_statement()
        return IfStmtNode(line=if_tok.line, column=if_tok.column, condition=cond, then_branch=then_branch, else_branch=else_branch)

    def _parse_while_stmt(self) -> WhileStmtNode:
        tok = self._consume(TokenType.KW_WHILE, "Expected 'while'")
        self._consume(TokenType.LPAREN, "Expected '(' after 'while'")
        cond = self._parse_expression()
        self._consume(TokenType.RPAREN, "Expected ')' after while condition")
        body = self._parse_statement()
        return WhileStmtNode(line=tok.line, column=tok.column, condition=cond, body=body)

    def _parse_for_stmt(self) -> ForStmtNode:
        tok = self._consume(TokenType.KW_FOR, "Expected 'for'")
        self._consume(TokenType.LPAREN, "Expected '(' after 'for'")
        
        init = None
        if not self._check(TokenType.SEMICOLON):
            if self._is_type_start():
                init = self._parse_var_decl() # includes trailing ';'
            else:
                init = self._parse_expression()
                self._consume(TokenType.SEMICOLON, "Expected ';' after for init")
        else:
            self._advance()

        cond = None
        if not self._check(TokenType.SEMICOLON):
            cond = self._parse_expression()
        self._consume(TokenType.SEMICOLON, "Expected ';' after for condition")

        update = None
        if not self._check(TokenType.RPAREN):
            update = self._parse_expression()
        self._consume(TokenType.RPAREN, "Expected ')' after for update")

        body = self._parse_statement()
        return ForStmtNode(line=tok.line, column=tok.column, init=init, condition=cond, update=update, body=body)

    def _parse_return_stmt(self) -> ReturnStmtNode:
        tok = self._consume(TokenType.KW_RETURN, "Expected 'return'")
        val = None
        if not self._check(TokenType.SEMICOLON):
            val = self._parse_expression()
        self._consume(TokenType.SEMICOLON, "Expected ';' after return")
        return ReturnStmtNode(line=tok.line, column=tok.column, value=val)

    # Expression parsing with precedence
    def _parse_expression(self) -> ASTNode:
        return self._parse_assignment()

    def _parse_assignment(self) -> ASTNode:
        node = self._parse_logical_or()
        assign_ops = {
            TokenType.ASSIGN: "=",
            TokenType.PLUS_ASSIGN: "+=",
            TokenType.MINUS_ASSIGN: "-=",
            TokenType.STAR_ASSIGN: "*=",
            TokenType.SLASH_ASSIGN: "/="
        }
        if self._peek().type in assign_ops:
            op_tok = self._advance()
            if not isinstance(node, VariableNode):
                raise ParserError("Invalid l-value for assignment", op_tok)
            val = self._parse_assignment()
            return AssignmentNode(
                line=op_tok.line, column=op_tok.column,
                target=node.name, op=assign_ops[op_tok.type], value=val
            )
        return node

    def _parse_logical_or(self) -> ASTNode:
        node = self._parse_logical_and()
        while self._match(TokenType.LOGICAL_OR):
            op = "||"
            right = self._parse_logical_and()
            node = BinaryOpNode(line=node.line, column=node.column, left=node, op=op, right=right)
        return node

    def _parse_logical_and(self) -> ASTNode:
        node = self._parse_bitwise_or()
        while self._match(TokenType.LOGICAL_AND):
            op = "&&"
            right = self._parse_bitwise_or()
            node = BinaryOpNode(line=node.line, column=node.column, left=node, op=op, right=right)
        return node

    def _parse_bitwise_or(self) -> ASTNode:
        node = self._parse_bitwise_xor()
        while self._match(TokenType.BIT_OR):
            op = "|"
            right = self._parse_bitwise_xor()
            node = BinaryOpNode(line=node.line, column=node.column, left=node, op=op, right=right)
        return node

    def _parse_bitwise_xor(self) -> ASTNode:
        node = self._parse_bitwise_and()
        while self._match(TokenType.BIT_XOR):
            op = "^"
            right = self._parse_bitwise_and()
            node = BinaryOpNode(line=node.line, column=node.column, left=node, op=op, right=right)
        return node

    def _parse_bitwise_and(self) -> ASTNode:
        node = self._parse_equality()
        while self._match(TokenType.BIT_AND):
            op = "&"
            right = self._parse_equality()
            node = BinaryOpNode(line=node.line, column=node.column, left=node, op=op, right=right)
        return node

    def _parse_equality(self) -> ASTNode:
        node = self._parse_relational()
        while self._peek().type in (TokenType.EQ, TokenType.NEQ):
            op_tok = self._advance()
            op = "==" if op_tok.type == TokenType.EQ else "!="
            right = self._parse_relational()
            node = BinaryOpNode(line=node.line, column=node.column, left=node, op=op, right=right)
        return node

    def _parse_relational(self) -> ASTNode:
        node = self._parse_shift()
        ops = {TokenType.LT: "<", TokenType.LTE: "<=", TokenType.GT: ">", TokenType.GTE: ">="}
        while self._peek().type in ops:
            op_tok = self._advance()
            op = ops[op_tok.type]
            right = self._parse_shift()
            node = BinaryOpNode(line=node.line, column=node.column, left=node, op=op, right=right)
        return node

    def _parse_shift(self) -> ASTNode:
        node = self._parse_additive()
        ops = {TokenType.LSHIFT: "<<", TokenType.RSHIFT: ">>"}
        while self._peek().type in ops:
            op_tok = self._advance()
            op = ops[op_tok.type]
            right = self._parse_additive()
            node = BinaryOpNode(line=node.line, column=node.column, left=node, op=op, right=right)
        return node

    def _parse_additive(self) -> ASTNode:
        node = self._parse_multiplicative()
        ops = {TokenType.PLUS: "+", TokenType.MINUS: "-"}
        while self._peek().type in ops:
            op_tok = self._advance()
            op = ops[op_tok.type]
            right = self._parse_multiplicative()
            node = BinaryOpNode(line=node.line, column=node.column, left=node, op=op, right=right)
        return node

    def _parse_multiplicative(self) -> ASTNode:
        node = self._parse_unary()
        ops = {TokenType.STAR: "*", TokenType.SLASH: "/", TokenType.PERCENT: "%"}
        while self._peek().type in ops:
            op_tok = self._advance()
            op = ops[op_tok.type]
            right = self._parse_unary()
            node = BinaryOpNode(line=node.line, column=node.column, left=node, op=op, right=right)
        return node

    def _parse_unary(self) -> ASTNode:
        tok = self._peek()
        if tok.type in (TokenType.MINUS, TokenType.PLUS, TokenType.LOGICAL_NOT, TokenType.BIT_NOT, TokenType.STAR):
            op_tok = self._advance()
            operand = self._parse_unary()
            return UnaryOpNode(line=op_tok.line, column=op_tok.column, op=str(op_tok.value), operand=operand, is_prefix=True)
        elif tok.type in (TokenType.INCREMENT, TokenType.DECREMENT):
            op_tok = self._advance()
            operand = self._parse_unary()
            return UnaryOpNode(line=op_tok.line, column=op_tok.column, op=str(op_tok.value), operand=operand, is_prefix=True)
        return self._parse_postfix()

    def _parse_postfix(self) -> ASTNode:
        node = self._parse_primary()
        while True:
            if self._match(TokenType.INCREMENT):
                node = UnaryOpNode(line=node.line, column=node.column, op="++", operand=node, is_prefix=False)
            elif self._match(TokenType.DECREMENT):
                node = UnaryOpNode(line=node.line, column=node.column, op="--", operand=node, is_prefix=False)
            elif self._match(TokenType.LBRACKET):
                index_expr = self._parse_expression()
                self._consume(TokenType.RBRACKET, "Expected ']'")
                node = BinaryOpNode(line=node.line, column=node.column, left=node, op="[]", right=index_expr)
            else:
                break
        return node

    def _parse_primary(self) -> ASTNode:
        tok = self._peek()

        if tok.type == TokenType.INT_LITERAL:
            self._advance()
            return LiteralNode(line=tok.line, column=tok.column, value=tok.value, lit_type="int")
        elif tok.type == TokenType.FLOAT_LITERAL:
            self._advance()
            return LiteralNode(line=tok.line, column=tok.column, value=tok.value, lit_type="float")
        elif tok.type == TokenType.STRING_LITERAL:
            self._advance()
            return LiteralNode(line=tok.line, column=tok.column, value=tok.value, lit_type="string")
        elif tok.type == TokenType.CHAR_LITERAL:
            self._advance()
            return LiteralNode(line=tok.line, column=tok.column, value=tok.value, lit_type="char")
        elif tok.type == TokenType.IDENTIFIER:
            ident_tok = self._advance()
            # Check for function call
            if self._match(TokenType.LPAREN):
                args = []
                if not self._check(TokenType.RPAREN):
                    while True:
                        args.append(self._parse_expression())
                        if not self._match(TokenType.COMMA):
                            break
                self._consume(TokenType.RPAREN, "Expected ')' after call arguments")
                return FunctionCallNode(line=ident_tok.line, column=ident_tok.column, name=ident_tok.value, args=args)
            return VariableNode(line=ident_tok.line, column=ident_tok.column, name=ident_tok.value)
        elif self._match(TokenType.LPAREN):
            expr = self._parse_expression()
            self._consume(TokenType.RPAREN, "Expected ')' to close parenthesis")
            return expr

        raise ParserError(f"Unexpected token in expression: {tok.value!r}", tok)
