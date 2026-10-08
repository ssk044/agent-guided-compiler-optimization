"""
Unit tests for Symbol Table and Semantic Analysis.
"""
from src.lexer import Lexer
from src.parser import Parser
from src.semantic import SemanticAnalyzer, SymbolTable, Symbol
from src.ast.nodes import TypeNode


def test_symbol_table_scoping():
    st = SymbolTable()
    s1 = Symbol("x", TypeNode("int"))
    assert st.define(s1) is True
    assert st.lookup("x") == s1

    # Enter nested scope
    st.enter_scope()
    s2 = Symbol("x", TypeNode("float"))
    assert st.define(s2) is True
    assert st.lookup("x") == s2 # Shadowed

    # Exit nested scope
    st.exit_scope()
    assert st.lookup("x") == s1


def test_semantic_analyzer_undeclared_variable():
    code = """
    int main() {
        int a = 10;
        b = 20; // undeclared
        return a;
    }
    """
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    analyzer = SemanticAnalyzer()
    diags = analyzer.analyze(ast)

    errors = [d for d in diags if d.severity == "ERROR"]
    assert len(errors) >= 1
    assert "undeclared" in errors[0].message.lower()


def test_semantic_analyzer_clean_code():
    code = """
    int square(int x) {
        return x * x;
    }
    int main() {
        int res = square(5);
        return res;
    }
    """
    tokens = Lexer(code).tokenize()
    ast = Parser(tokens).parse()
    analyzer = SemanticAnalyzer()
    diags = analyzer.analyze(ast)
    errors = [d for d in diags if d.severity == "ERROR"]
    assert len(errors) == 0
