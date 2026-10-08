"""
Token definitions for the C/C++ lexer.
"""
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class TokenType(Enum):
    # Keywords
    KW_INT = auto()
    KW_FLOAT = auto()
    KW_DOUBLE = auto()
    KW_CHAR = auto()
    KW_VOID = auto()
    KW_IF = auto()
    KW_ELSE = auto()
    KW_WHILE = auto()
    KW_FOR = auto()
    KW_RETURN = auto()
    KW_CONST = auto()
    KW_STATIC = auto()
    KW_SIZEOF = auto()

    # Literals & Identifiers
    IDENTIFIER = auto()
    INT_LITERAL = auto()
    FLOAT_LITERAL = auto()
    STRING_LITERAL = auto()
    CHAR_LITERAL = auto()

    # Operators
    PLUS = auto()           # +
    MINUS = auto()          # -
    STAR = auto()           # *
    SLASH = auto()          # /
    PERCENT = auto()        # %
    ASSIGN = auto()         # =
    PLUS_ASSIGN = auto()    # +=
    MINUS_ASSIGN = auto()   # -=
    STAR_ASSIGN = auto()    # *=
    SLASH_ASSIGN = auto()   # /=
    
    # Comparison
    EQ = auto()             # ==
    NEQ = auto()            # !=
    LT = auto()             # <
    LTE = auto()            # <=
    GT = auto()             # >
    GTE = auto()            # >=

    # Logical & Bitwise
    LOGICAL_AND = auto()    # &&
    LOGICAL_OR = auto()     # ||
    LOGICAL_NOT = auto()    # !
    BIT_AND = auto()        # &
    BIT_OR = auto()         # |
    BIT_XOR = auto()        # ^
    BIT_NOT = auto()        # ~
    LSHIFT = auto()         # <<
    RSHIFT = auto()         # >>

    # Increment / Decrement
    INCREMENT = auto()      # ++
    DECREMENT = auto()      # --

    # Delimiters
    LPAREN = auto()         # (
    RPAREN = auto()         # )
    LBRACE = auto()         # {
    RBRACE = auto()         # }
    LBRACKET = auto()       # [
    RBRACKET = auto()       # ]
    SEMICOLON = auto()      # ;
    COMMA = auto()          # ,
    DOT = auto()            # .
    ARROW = auto()          # ->
    COLON = auto()          # :
    QUESTION = auto()       # ?

    # Special
    EOF = auto()
    UNKNOWN = auto()


KEYWORDS = {
    "int": TokenType.KW_INT,
    "float": TokenType.KW_FLOAT,
    "double": TokenType.KW_DOUBLE,
    "char": TokenType.KW_CHAR,
    "void": TokenType.KW_VOID,
    "if": TokenType.KW_IF,
    "else": TokenType.KW_ELSE,
    "while": TokenType.KW_WHILE,
    "for": TokenType.KW_FOR,
    "return": TokenType.KW_RETURN,
    "const": TokenType.KW_CONST,
    "static": TokenType.KW_STATIC,
    "sizeof": TokenType.KW_SIZEOF,
}


@dataclass
class Token:
    type: TokenType
    value: Any
    line: int
    column: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, line={self.line}, col={self.column})"
