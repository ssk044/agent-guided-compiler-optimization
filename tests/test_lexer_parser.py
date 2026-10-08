"""
Unit tests for Lexer, Parser, and AST representations.
"""
from src.lexer import Lexer, TokenType
from src.parser import Parser
from src.ast import ASTPrinter, ProgramNode, FunctionDefNode, BinaryOpNode, LiteralNode


def test_lexer_tokens():
    source = "int x = 42 + 0x10; // comment\nfloat y = 3.14;"
    lexer = Lexer(source)
    tokens = lexer.tokenize()

    assert tokens[0].type == TokenType.KW_INT
    assert tokens[1].type == TokenType.IDENTIFIER and tokens[1].value == "x"
    assert tokens[2].type == TokenType.ASSIGN
    assert tokens[3].type == TokenType.INT_LITERAL and tokens[3].value == 42
    assert tokens[4].type == TokenType.PLUS
    assert tokens[5].type == TokenType.INT_LITERAL and tokens[5].value == 16
    assert tokens[6].type == TokenType.SEMICOLON


def test_parser_function_and_expressions():
    code = """
    int add(int a, int b) {
        int res = a + b * 2;
        return res;
    }
    """
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    prog = parser.parse()

    assert isinstance(prog, ProgramNode)
    assert len(prog.declarations) == 1
    fn = prog.declarations[0]
    assert isinstance(fn, FunctionDefNode)
    assert fn.name == "add"
    assert len(fn.params) == 2

    # Verify precedence: a + (b * 2)
    # The initializer of res should be a BinaryOp '+' with right operand BinaryOp '*'
    decl_res = fn.body.statements[0]
    init = decl_res.initializer
    assert isinstance(init, BinaryOpNode)
    assert init.op == "+"
    assert isinstance(init.right, BinaryOpNode)
    assert init.right.op == "*"


def test_ast_printer():
    code = "int main() { return 0; }"
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    printer = ASTPrinter()
    tree = printer.print_tree(ast)
    assert "FunctionDef: int main()" in tree
    assert "Return" in tree
