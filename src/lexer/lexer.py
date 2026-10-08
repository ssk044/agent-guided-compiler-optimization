"""
Lexer for C/C++ source code subset.
"""
from typing import List, Optional
from src.lexer.tokens import Token, TokenType, KEYWORDS


class LexerError(Exception):
    def __init__(self, message: str, line: int, column: int):
        super().__init__(f"Lexer error at line {line}, col {column}: {message}")
        self.line = line
        self.column = column


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.length = len(source)
        self.pos = 0
        self.line = 1
        self.column = 1

    def _peek(self, offset: int = 0) -> Optional[str]:
        target = self.pos + offset
        if target < self.length:
            return self.source[target]
        return None

    def _advance(self) -> Optional[str]:
        if self.pos < self.length:
            ch = self.source[self.pos]
            self.pos += 1
            if ch == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            return ch
        return None

    def _match(self, expected: str) -> bool:
        if self._peek() == expected:
            self._advance()
            return True
        return False

    def _skip_whitespace_and_comments(self) -> None:
        while self.pos < self.length:
            ch = self._peek()
            if ch in (' ', '\t', '\r', '\n'):
                self._advance()
            elif ch == '/' and self._peek(1) == '/':
                # Single-line comment
                while self.pos < self.length and self._peek() != '\n':
                    self._advance()
            elif ch == '/' and self._peek(1) == '*':
                # Multi-line comment
                start_line = self.line
                start_col = self.column
                self._advance() # /
                self._advance() # *
                closed = False
                while self.pos < self.length:
                    if self._peek() == '*' and self._peek(1) == '/':
                        self._advance()
                        self._advance()
                        closed = True
                        break
                    self._advance()
                if not closed:
                    raise LexerError("Unterminated multi-line comment", start_line, start_col)
            elif ch == '#':
                # Preprocessor directive (e.g. #include <stdio.h>), skip entire line
                while self.pos < self.length and self._peek() != '\n':
                    self._advance()
            else:
                break

    def _read_number(self, start_line: int, start_col: int) -> Token:
        num_str = ""
        is_float = False
        is_hex = False

        if self._peek() == '0' and self._peek(1) in ('x', 'X'):
            num_str += self._advance() # 0
            num_str += self._advance() # x
            is_hex = True
            while self._peek() and (self._peek().isdigit() or self._peek().lower() in 'abcdef'):
                num_str += self._advance()
            return Token(TokenType.INT_LITERAL, int(num_str, 16), start_line, start_col)

        while self._peek() and (self._peek().isdigit() or self._peek() == '.'):
            if self._peek() == '.':
                if is_float:
                    break
                is_float = True
            num_str += self._advance()

        if is_float:
            return Token(TokenType.FLOAT_LITERAL, float(num_str), start_line, start_col)
        return Token(TokenType.INT_LITERAL, int(num_str), start_line, start_col)

    def _read_identifier_or_keyword(self, start_line: int, start_col: int) -> Token:
        ident = ""
        while self._peek() and (self._peek().isalnum() or self._peek() == '_'):
            ident += self._advance()

        tok_type = KEYWORDS.get(ident, TokenType.IDENTIFIER)
        return Token(tok_type, ident, start_line, start_col)

    def _read_string(self, start_line: int, start_col: int) -> Token:
        self._advance() # skip opening quote "
        val = ""
        escape = False
        while self.pos < self.length:
            ch = self._advance()
            if escape:
                if ch == 'n': val += '\n'
                elif ch == 't': val += '\t'
                elif ch == 'r': val += '\r'
                elif ch == '\\': val += '\\'
                elif ch == '"': val += '"'
                elif ch == '0': val += '\0'
                else: val += ch
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == '"':
                return Token(TokenType.STRING_LITERAL, val, start_line, start_col)
            else:
                val += ch
        raise LexerError("Unterminated string literal", start_line, start_col)

    def _read_char(self, start_line: int, start_col: int) -> Token:
        self._advance() # skip opening '
        if self._peek() == '\\':
            self._advance()
            esc = self._advance()
            char_val = '\n' if esc == 'n' else ('\t' if esc == 't' else esc)
        else:
            char_val = self._advance()
        if self._advance() != "'":
            raise LexerError("Unterminated character literal", start_line, start_col)
        return Token(TokenType.CHAR_LITERAL, char_val, start_line, start_col)

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        while self.pos < self.length:
            self._skip_whitespace_and_comments()
            if self.pos >= self.length:
                break

            start_line = self.line
            start_col = self.column
            ch = self._peek()

            if ch.isdigit():
                tokens.append(self._read_number(start_line, start_col))
            elif ch.isalpha() or ch == '_':
                tokens.append(self._read_identifier_or_keyword(start_line, start_col))
            elif ch == '"':
                tokens.append(self._read_string(start_line, start_col))
            elif ch == "'":
                tokens.append(self._read_char(start_line, start_col))
            elif ch == '+':
                self._advance()
                if self._match('+'):
                    tokens.append(Token(TokenType.INCREMENT, "++", start_line, start_col))
                elif self._match('='):
                    tokens.append(Token(TokenType.PLUS_ASSIGN, "+=", start_line, start_col))
                else:
                    tokens.append(Token(TokenType.PLUS, "+", start_line, start_col))
            elif ch == '-':
                self._advance()
                if self._match('-'):
                    tokens.append(Token(TokenType.DECREMENT, "--", start_line, start_col))
                elif self._match('='):
                    tokens.append(Token(TokenType.MINUS_ASSIGN, "-=", start_line, start_col))
                elif self._match('>'):
                    tokens.append(Token(TokenType.ARROW, "->", start_line, start_col))
                else:
                    tokens.append(Token(TokenType.MINUS, "-", start_line, start_col))
            elif ch == '*':
                self._advance()
                if self._match('='):
                    tokens.append(Token(TokenType.STAR_ASSIGN, "*=", start_line, start_col))
                else:
                    tokens.append(Token(TokenType.STAR, "*", start_line, start_col))
            elif ch == '/':
                self._advance()
                if self._match('='):
                    tokens.append(Token(TokenType.SLASH_ASSIGN, "/=", start_line, start_col))
                else:
                    tokens.append(Token(TokenType.SLASH, "/", start_line, start_col))
            elif ch == '%':
                self._advance()
                tokens.append(Token(TokenType.PERCENT, "%", start_line, start_col))
            elif ch == '=':
                self._advance()
                if self._match('='):
                    tokens.append(Token(TokenType.EQ, "==", start_line, start_col))
                else:
                    tokens.append(Token(TokenType.ASSIGN, "=", start_line, start_col))
            elif ch == '!':
                self._advance()
                if self._match('='):
                    tokens.append(Token(TokenType.NEQ, "!=", start_line, start_col))
                else:
                    tokens.append(Token(TokenType.LOGICAL_NOT, "!", start_line, start_col))
            elif ch == '<':
                self._advance()
                if self._match('='):
                    tokens.append(Token(TokenType.LTE, "<=", start_line, start_col))
                elif self._match('<'):
                    tokens.append(Token(TokenType.LSHIFT, "<<", start_line, start_col))
                else:
                    tokens.append(Token(TokenType.LT, "<", start_line, start_col))
            elif ch == '>':
                self._advance()
                if self._match('='):
                    tokens.append(Token(TokenType.GTE, ">=", start_line, start_col))
                elif self._match('>'):
                    tokens.append(Token(TokenType.RSHIFT, ">>", start_line, start_col))
                else:
                    tokens.append(Token(TokenType.GT, ">", start_line, start_col))
            elif ch == '&':
                self._advance()
                if self._match('&'):
                    tokens.append(Token(TokenType.LOGICAL_AND, "&&", start_line, start_col))
                else:
                    tokens.append(Token(TokenType.BIT_AND, "&", start_line, start_col))
            elif ch == '|':
                self._advance()
                if self._match('|'):
                    tokens.append(Token(TokenType.LOGICAL_OR, "||", start_line, start_col))
                else:
                    tokens.append(Token(TokenType.BIT_OR, "|", start_line, start_col))
            elif ch == '^':
                self._advance()
                tokens.append(Token(TokenType.BIT_XOR, "^", start_line, start_col))
            elif ch == '~':
                self._advance()
                tokens.append(Token(TokenType.BIT_NOT, "~", start_line, start_col))
            elif ch == '(':
                self._advance()
                tokens.append(Token(TokenType.LPAREN, "(", start_line, start_col))
            elif ch == ')':
                self._advance()
                tokens.append(Token(TokenType.RPAREN, ")", start_line, start_col))
            elif ch == '{':
                self._advance()
                tokens.append(Token(TokenType.LBRACE, "{", start_line, start_col))
            elif ch == '}':
                self._advance()
                tokens.append(Token(TokenType.RBRACE, "}", start_line, start_col))
            elif ch == '[':
                self._advance()
                tokens.append(Token(TokenType.LBRACKET, "[", start_line, start_col))
            elif ch == ']':
                self._advance()
                tokens.append(Token(TokenType.RBRACKET, "]", start_line, start_col))
            elif ch == ';':
                self._advance()
                tokens.append(Token(TokenType.SEMICOLON, ";", start_line, start_col))
            elif ch == ',':
                self._advance()
                tokens.append(Token(TokenType.COMMA, ",", start_line, start_col))
            elif ch == ':':
                self._advance()
                tokens.append(Token(TokenType.COLON, ":", start_line, start_col))
            elif ch == '?':
                self._advance()
                tokens.append(Token(TokenType.QUESTION, "?", start_line, start_col))
            else:
                bad_char = self._advance()
                raise LexerError(f"Unexpected character '{bad_char}'", start_line, start_col)

        tokens.append(Token(TokenType.EOF, None, self.line, self.column))
        return tokens
