"""PLY Lex implementation for the Phase 1 Mini-C lexical grammar."""

from __future__ import annotations

import ast
import math
import re
from dataclasses import dataclass
from typing import Any, Iterator

import ply.lex as lex

from .errors import LexicalError
from .source_location import SourceLocation, SourceSpan


@dataclass(frozen=True, slots=True)
class TokenInfo:
    type: str
    lexeme: str
    value: Any
    span: SourceSpan

    @property
    def line(self) -> int:
        return self.span.start.line

    @property
    def column(self) -> int:
        return self.span.start.column

    @property
    def offset(self) -> int:
        return self.span.start.offset

    @property
    def lineno(self) -> int:
        """PLY Yacc-compatible line attribute."""
        return self.line

    @property
    def lexpos(self) -> int:
        """PLY Yacc-compatible source-offset attribute."""
        return self.offset

    def to_dict(self) -> dict[str, object]:
        return {
            "type": self.type,
            "lexeme": self.lexeme,
            "value": self.value,
            "line": self.line,
            "column": self.column,
            "offset": self.offset,
            "span": self.span.to_dict(),
        }


class MiniCLexer:
    """Reusable lexer whose deterministic output is never silently corrected."""

    reserved = {
        "int": "INT",
        "float": "FLOAT",
        "char": "CHAR",
        "bool": "BOOL",
        "void": "VOID",
        "if": "IF",
        "else": "ELSE",
        "while": "WHILE",
        "for": "FOR",
        "break": "BREAK",
        "continue": "CONTINUE",
        "return": "RETURN",
        "true": "TRUE",
        "false": "FALSE",
    }

    tokens = (
        "IDENTIFIER",
        "INTEGER_LITERAL",
        "FLOAT_LITERAL",
        "CHAR_LITERAL",
        "STRING_LITERAL",
        "PLUS",
        "MINUS",
        "TIMES",
        "DIVIDE",
        "MODULO",
        "ASSIGN",
        "PLUS_ASSIGN",
        "MINUS_ASSIGN",
        "TIMES_ASSIGN",
        "DIVIDE_ASSIGN",
        "MODULO_ASSIGN",
        "INCREMENT",
        "DECREMENT",
        "LT",
        "GT",
        "LE",
        "GE",
        "EQ",
        "NE",
        "AND",
        "OR",
        "NOT",
        "SEMICOLON",
        "COMMA",
        "DOT",
        "LPAREN",
        "RPAREN",
        "LBRACE",
        "RBRACE",
        "LBRACKET",
        "RBRACKET",
        *reserved.values(),
    )

    t_PLUS_ASSIGN = r"\+="
    t_MINUS_ASSIGN = r"-="
    t_TIMES_ASSIGN = r"\*="
    t_DIVIDE_ASSIGN = r"/="
    t_MODULO_ASSIGN = r"%="
    t_INCREMENT = r"\+\+"
    t_DECREMENT = r"--"
    t_LE = r"<="
    t_GE = r">="
    t_EQ = r"=="
    t_NE = r"!="
    t_AND = r"&&"
    t_OR = r"\|\|"
    t_PLUS = r"\+"
    t_MINUS = r"-"
    t_TIMES = r"\*"
    t_DIVIDE = r"/"
    t_MODULO = r"%"
    t_ASSIGN = r"="
    t_LT = r"<"
    t_GT = r">"
    t_NOT = r"!"
    t_SEMICOLON = r";"
    t_COMMA = r","
    t_DOT = r"\."
    t_LPAREN = r"\("
    t_RPAREN = r"\)"
    t_LBRACE = r"\{"
    t_RBRACE = r"\}"
    t_LBRACKET = r"\["
    t_RBRACKET = r"\]"
    t_ignore = " \t\f\v"

    def __init__(self) -> None:
        self.errors: list[LexicalError] = []
        self.source = ""
        self._lexer = lex.lex(module=self, reflags=0)

    def input(self, source: str) -> None:
        self.source = source
        self.errors.clear()
        self._lexer.lineno = 1
        self._lexer.input(source)

    def token(self) -> TokenInfo | None:
        raw = self._lexer.token()
        if raw is None:
            return None
        lexeme = self.source[raw.lexpos : self._lexer.lexpos]
        span = self._span(raw.lexpos, self._lexer.lexpos)
        return TokenInfo(raw.type, lexeme, raw.value, span)

    def __iter__(self) -> Iterator[TokenInfo]:
        while (token := self.token()) is not None:
            yield token

    def scan(self, source: str) -> tuple[list[TokenInfo], list[LexicalError]]:
        self.input(source)
        return list(self), list(self.errors)

    def _location(self, offset: int) -> SourceLocation:
        line = self.source.count("\n", 0, offset) + 1
        last_newline = self.source.rfind("\n", 0, offset)
        column = offset + 1 if last_newline < 0 else offset - last_newline
        return SourceLocation(line, column, offset)

    def _span(self, start: int, end: int) -> SourceSpan:
        return SourceSpan(self._location(start), self._location(end))

    def _error(self, code: str, message: str, lexeme: str, start: int, end: int) -> None:
        self.errors.append(LexicalError("lexical", code, message, lexeme, self._span(start, end)))

    def t_BLOCK_COMMENT(self, token):
        r"/\*[\s\S]*?\*/"
        token.lexer.lineno += token.value.count("\n")

    def t_UNTERMINATED_BLOCK_COMMENT(self, token):
        r"/\*[\s\S]*"
        start = token.lexpos
        token.lexer.lineno += token.value.count("\n")
        self._error(
            "UNTERMINATED_COMMENT",
            "Unterminated multi-line comment",
            token.value,
            start,
            start + len(token.value),
        )

    @staticmethod
    def _contains_invalid_escape(text: str) -> bool:
        r"""Validate escape sequences before Python decodes a literal.

        Accept simple C escapes, one-to-three-digit octal escapes, two-digit
        hexadecimal escapes, and Python-compatible ``\u``/``\U`` Unicode
        escapes. Unknown or incomplete escapes (for example, ``\q``) are
        diagnosed instead of being silently preserved by Python.
        """
        index = 0
        hex_digits = set("0123456789abcdefABCDEF")
        simple_escapes = set("abfnrtv\\'\"?")
        while index < len(text):
            if text[index] != "\\":
                index += 1
                continue
            if index + 1 >= len(text):
                return True
            code = text[index + 1]
            if code in simple_escapes:
                index += 2
            elif code in "01234567":
                index += 2
                end = index + 2
                while index < len(text) and index < end and text[index] in "01234567":
                    index += 1
            elif code == "x":
                digits = text[index + 2:index + 4]
                if len(digits) != 2 or any(char not in hex_digits for char in digits):
                    return True
                index += 4
            elif code == "u":
                digits = text[index + 2:index + 6]
                if len(digits) != 4 or any(char not in hex_digits for char in digits):
                    return True
                index += 6
            elif code == "U":
                digits = text[index + 2:index + 10]
                if len(digits) != 8 or any(char not in hex_digits for char in digits):
                    return True
                index += 10
            else:
                return True
        return False

    def t_LINE_COMMENT(self, token):
        r"//[^\r\n]*"

    def t_MALFORMED_NUMBER(self, token):
        # Keep malformed number-shaped input inside the lexer so that values such
        # as 1e+, .5e-, 3._4, and 1e3suffix are not split into unrelated tokens.
        r"(?:\.\.\d+(?:\.\d*)?|(?:\d+(?:\.\d*)?|\.\d+)[eE](?:[+-][+-]+\d*|[+-](?!\d)|(?=[^+\-\d]|$))(?:[A-Za-z_]\w*)?|(?:\d+(?:\.\d*)?|\.\d+)[eE][+-]?\d+[A-Za-z_]\w*|\d+\.\d*\.\d*|\d+\.\d*[A-DF-Za-df-z_]\w*|\d+[A-DF-Za-df-z_]\w*)"
        self._error(
            "MALFORMED_NUMBER",
            f"Malformed numeric literal {token.value!r}",
            token.value,
            token.lexpos,
            token.lexpos + len(token.value),
        )

    def t_FLOAT_LITERAL(self, token):
        r"(?:\d+\.\d*|\.\d+)(?:[eE][+-]?\d+)?|\d+[eE][+-]?\d+"
        try:
            value = float(token.value)
        except (OverflowError, ValueError):
            value = math.inf
        if not math.isfinite(value):
            self._error(
                "NUMERIC_LITERAL_OUT_OF_RANGE",
                f"Floating-point literal {token.value!r} is outside the supported finite range",
                token.value,
                token.lexpos,
                token.lexpos + len(token.value),
            )
            return None
        token.value = value
        return token

    def t_INTEGER_LITERAL(self, token):
        r"\d+"
        token.value = int(token.value)
        return token

    def t_STRING_LITERAL(self, token):
        r'"(?:[^"\\\r\n]|\\.)*"'
        if self._contains_invalid_escape(token.value[1:-1]):
            self._error(
                "MALFORMED_STRING",
                "String literal contains an unsupported or incomplete escape sequence",
                token.value,
                token.lexpos,
                token.lexpos + len(token.value),
            )
            return None
        try:
            token.value = ast.literal_eval(token.value)
        except (SyntaxError, ValueError):
            self._error(
                "MALFORMED_STRING",
                "Malformed string literal",
                token.value,
                token.lexpos,
                token.lexpos + len(token.value),
            )
            return None
        return token

    def t_UNTERMINATED_STRING(self, token):
        r'"(?:[^"\\\r\n]|\\.)*(?:\r?\n|$)'
        lexeme = token.value.rstrip("\r\n")
        self._error(
            "UNTERMINATED_STRING",
            "Unterminated string literal",
            lexeme,
            token.lexpos,
            token.lexpos + len(lexeme),
        )
        token.lexer.lineno += token.value.count("\n")

    def t_CHAR_LITERAL(self, token):
        r"'(?:[^'\\\r\n]|\\(?:[abfnrtv\\'\"?]|[0-7]{1,3}|x[0-9A-Fa-f]{2}|.))'"
        if self._contains_invalid_escape(token.value[1:-1]):
            self._error(
                "MALFORMED_CHAR",
                "Character literal contains an unsupported or incomplete escape sequence",
                token.value,
                token.lexpos,
                token.lexpos + len(token.value),
            )
            return None
        try:
            token.value = ast.literal_eval(token.value)
        except (SyntaxError, ValueError):
            self._error(
                "MALFORMED_CHAR",
                "Malformed character literal",
                token.value,
                token.lexpos,
                token.lexpos + len(token.value),
            )
            return None
        return token

    def t_MALFORMED_CHAR(self, token):
        r"'(?:[^'\\\r\n]|\\.)*(?:'|\r?\n|$)"
        lexeme = token.value.rstrip("\r\n")
        closed = lexeme.endswith("'") and len(lexeme) > 1
        code = "MALFORMED_CHAR" if closed else "UNTERMINATED_CHAR"
        message = "Malformed character literal" if closed else "Unterminated character literal"
        self._error(code, message, lexeme, token.lexpos, token.lexpos + len(lexeme))
        token.lexer.lineno += token.value.count("\n")

    def t_IDENTIFIER(self, token):
        r"[A-Za-z_]\w*"
        token.type = self.reserved.get(token.value, "IDENTIFIER")
        if token.type == "TRUE":
            token.value = True
        elif token.type == "FALSE":
            token.value = False
        return token

    def t_newline(self, token):
        r"\r?\n+"
        token.lexer.lineno += token.value.count("\n")

    def t_error(self, token):
        lexeme = token.value[0]
        self._error(
            "ILLEGAL_CHARACTER",
            f"Illegal character {lexeme!r}",
            lexeme,
            token.lexpos,
            token.lexpos + 1,
        )
        token.lexer.skip(1)


def tokenize(source: str) -> tuple[list[TokenInfo], list[LexicalError]]:
    """Convenience function for one-shot lexical analysis."""

    return MiniCLexer().scan(source)
