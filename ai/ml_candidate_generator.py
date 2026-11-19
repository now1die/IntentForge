"""Translate trained ML correction classes into minimal, source-located edits.

The classifier predicts the repair family; this module instantiates only edits
that match the source/context. Every edit is still run through the real Mini-C
parser (and semantic analyzer for array-call repairs) before it can be applied.
"""
from __future__ import annotations

import re
from typing import Iterable

from compiler.correction import CorrectionAction, CorrectionCandidate, CorrectionEdit
from compiler.errors import SyntaxDiagnostic
from compiler.source_location import SourceLocation, SourceSpan

from .dataset_generator import CorrectionClass
from .error_context import ErrorContext
from .error_predictor import ErrorPrediction


def _location(source: str, offset: int) -> SourceLocation:
    line = source.count("\n", 0, offset) + 1
    last_newline = source.rfind("\n", 0, offset)
    column = offset + 1 if last_newline < 0 else offset - last_newline
    return SourceLocation(line, column, offset)


def _span(source: str, start: int, end: int) -> SourceSpan:
    return SourceSpan(_location(source, start), _location(source, end))


def _candidate(
    source: str,
    diagnostic_id: str,
    action: CorrectionAction,
    token_type: str,
    lexeme: str,
    offset: int,
    end: int,
    text: str,
    grammar_context: str,
    reason: str,
) -> CorrectionCandidate:
    return CorrectionCandidate(
        id=f"{diagnostic_id}-ML01",
        action=action,
        token_type=token_type,
        token_lexeme=lexeme,
        offset=offset,
        span=_span(source, offset, end),
        text=text,
        reason=reason,
        grammar_context=grammar_context,
        diagnostic_id=diagnostic_id,
        origin="ml_predicted_class",
    )


def _inside_condition(source: str, offset: int) -> bool:
    """Conservatively identify whether an offset lies inside a control header.

    Unlike if/while conditions, a for-header legitimately contains semicolons,
    so using a generic semicolon split accidentally excluded its condition.
    """
    prefix = source[:offset]
    controls = list(re.finditer(r"\b(if|while|for)\s*\(", prefix))
    for match in reversed(controls):
        opening = match.end() - 1
        # A completed header or a brace between the opener and the target means
        # the offset is not inside this header.
        closing = source.find(")", opening + 1)
        if closing < 0 or closing < offset:
            continue
        segment = source[opening + 1:offset]
        if "{" in segment or "}" in segment:
            continue
        return True
    return False


def _array_names(source: str) -> set[str]:
    return set(re.findall(r"\b(?:int|float|char|bool)\s+([A-Za-z_]\w*)\s*\[", source))


def _compound_array_call_candidate(
    source: str, diagnostic: SyntaxDiagnostic, context: ErrorContext
) -> tuple[CorrectionCandidate, ...]:
    """Convert arr(expr) to arr[expr] only when arr is declared as an array."""
    array_names = _array_names(source)
    matches: list[tuple[int, int, int, str]] = []
    for name in array_names:
        for match in re.finditer(rf"\b{re.escape(name)}\s*\(([^()]*?)\)", source):
            open_offset = source.find("(", match.start(), match.end())
            close_offset = match.end() - 1
            distance = min(
                abs(open_offset - diagnostic.span.start.offset),
                abs(match.start() - diagnostic.span.start.offset),
            )
            matches.append((distance, open_offset, close_offset, match.group(0)))
    if not matches:
        return ()
    _, open_offset, close_offset, original = min(matches, key=lambda item: item[0])
    open_span = _span(source, open_offset, open_offset + 1)
    close_span = _span(source, close_offset, close_offset + 1)
    edits = (
        CorrectionEdit(CorrectionAction.REPLACE, "LBRACKET", "(", open_offset, open_span, "["),
        CorrectionEdit(CorrectionAction.REPLACE, "RBRACKET", ")", close_offset, close_span, "]"),
    )
    full_span = _span(source, open_offset, close_offset + 1)
    return (
        CorrectionCandidate(
            id=f"{diagnostic.diagnostic_id}-ML01",
            action=CorrectionAction.COMPOUND,
            token_type="LBRACKET",
            token_lexeme="()",
            offset=open_offset,
            span=full_span,
            text="[]",
            reason="ML predicted ARRAY_CALL_ERROR for a declared array",
            grammar_context="array_access",
            diagnostic_id=diagnostic.diagnostic_id,
            origin="ml_predicted_class",
            edits=edits,
        ),
    )


def _declaration_open_paren(source: str, before_offset: int) -> int | None:
    """Find a parenthesis used as an array-declaration opener, not a function."""
    prefix = source[: max(0, before_offset + 1)]
    candidates = list(re.finditer(r"\b(?:int|float|char|bool)\s+[A-Za-z_]\w*\s*\(", prefix))
    for match in reversed(candidates):
        # A function signature has ')' before '{'; array-declaration corruption
        # typically has ']' before ';'.
        tail = source[match.end() :]
        semicolon = tail.find(";")
        brace = tail.find("{")
        bracket = tail.find("]")
        if bracket >= 0 and (semicolon < 0 or bracket < semicolon) and (brace < 0 or bracket < brace):
            return match.end() - 1
    return None


def generate_ml_candidates(
    source: str,
    diagnostic: SyntaxDiagnostic,
    context: ErrorContext,
    prediction: ErrorPrediction,
) -> tuple[CorrectionCandidate, ...]:
    """Create minimal edits implied by the predicted ML class and local context."""
    label = prediction.label
    offset = diagnostic.span.start.offset
    end = diagnostic.span.end.offset
    lexeme = diagnostic.unexpected_lexeme or ""
    grammar = context.grammar_context or diagnostic.grammar_context or "unknown"
    candidates: list[CorrectionCandidate] = []

    if label == CorrectionClass.ARRAY_CALL_ERROR.value:
        return _compound_array_call_candidate(source, diagnostic, context)

    if label == CorrectionClass.REPAIR_MISMATCHED_DELIMITER.value:
        # Learned compound repair: replace a mismatched `]` at the end of a
        # nested condition, then close the remaining `(` before the body.
        condition_start = source.rfind("if", 0, max(0, offset + 1))
        if condition_start < 0:
            condition_start = source.rfind("while", 0, max(0, offset + 1))
        bracket = offset if source[offset:offset + 1] == "]" else source.find("]", max(0, offset - 12), min(len(source), offset + 24))
        if bracket >= 0 and condition_start >= 0:
            brace = source.find("{", bracket, min(len(source), bracket + 80))
            if brace >= 0:
                condition_segment = source[condition_start:bracket + 1]
                balance = condition_segment.count("(") - condition_segment.count(")")
                if balance >= 2:
                    insert_at = brace
                    while insert_at > bracket and source[insert_at - 1].isspace():
                        insert_at -= 1
                    edits = (
                        CorrectionEdit(CorrectionAction.REPLACE, "RPAREN", "]", bracket,
                            _span(source, bracket, bracket + 1), ")"),
                        CorrectionEdit(CorrectionAction.INSERT, "RPAREN", ")", insert_at,
                            _span(source, insert_at, insert_at), ")"),
                    )
                    return (CorrectionCandidate(
                        id=f"{diagnostic.diagnostic_id}-ML01", action=CorrectionAction.COMPOUND,
                        token_type="COMPOUND", token_lexeme="]", offset=bracket,
                        span=_span(source, bracket, brace), text="))",
                        reason="ML predicted REPAIR_MISMATCHED_DELIMITER",
                        grammar_context=grammar, diagnostic_id=diagnostic.diagnostic_id,
                        origin="ml_predicted_class", edits=edits,
                    ),)

    expected = set(diagnostic.expected_tokens or context.expected_tokens)

    # The core missing-token classes are instantiated from the model prediction
    # and parser's expected-token evidence. Parser validation remains mandatory.
    if label == CorrectionClass.INSERT_SEMICOLON.value and "SEMICOLON" in expected:
        return (_candidate(source, diagnostic.diagnostic_id, CorrectionAction.INSERT,
            "SEMICOLON", None, offset, offset, ";", grammar, "ML predicted INSERT_SEMICOLON"),)

    if label == CorrectionClass.INSERT_RPAREN.value:
        # A mismatched closer plus another open condition parenthesis requires a
        # coordinated edit: repair the closer, then close the remaining paren.
        brace = source.find("{", max(0, offset), min(len(source), offset + 80))
        close_bracket = source.find("]", max(0, offset - 8), brace if brace >= 0 else min(len(source), offset + 80))
        if brace >= 0 and close_bracket >= 0 and close_bracket <= brace:
            segment = source[:close_bracket + 1]
            balance = segment.count("(") - segment.count(")")
            if balance >= 2:
                insert_at = brace
                while insert_at > close_bracket and source[insert_at - 1].isspace():
                    insert_at -= 1
                edits = (
                    CorrectionEdit(CorrectionAction.REPLACE, "RPAREN", "]", close_bracket,
                        _span(source, close_bracket, close_bracket + 1), ")"),
                    CorrectionEdit(CorrectionAction.INSERT, "RPAREN", ")", insert_at,
                        _span(source, insert_at, insert_at), ")"),
                )
                return (CorrectionCandidate(
                    id=f"{diagnostic.diagnostic_id}-ML01", action=CorrectionAction.COMPOUND,
                    token_type="COMPOUND", token_lexeme="]", offset=close_bracket,
                    span=_span(source, close_bracket, brace), text="))",
                    reason="ML predicted INSERT_RPAREN; repair mismatched closer and close condition",
                    grammar_context=grammar, diagnostic_id=diagnostic.diagnostic_id,
                    origin="ml_predicted_class", edits=edits,
                ),)
        if "RPAREN" in expected:
            return (_candidate(source, diagnostic.diagnostic_id, CorrectionAction.INSERT,
                "RPAREN", None, offset, offset, ")", grammar, "ML predicted INSERT_RPAREN"),)

    if label == CorrectionClass.INSERT_LPAREN.value:
        if "LPAREN" in expected:
            return (_candidate(source, diagnostic.diagnostic_id, CorrectionAction.INSERT,
                "LPAREN", None, offset, offset, "(", grammar, "ML predicted INSERT_LPAREN"),)
        match = re.search(r"\b(?:if|while|for)\b(?!\s*\()", source)
        if match:
            insert_at = match.end()
            return (_candidate(source, diagnostic.diagnostic_id, CorrectionAction.INSERT,
                "LPAREN", None, insert_at, insert_at, "(", "if_condition",
                "ML predicted INSERT_LPAREN"),)

    if label == CorrectionClass.INSERT_RBRACKET.value and "RBRACKET" in expected:
        return (_candidate(source, diagnostic.diagnostic_id, CorrectionAction.INSERT,
            "RBRACKET", None, offset, offset, "]", grammar, "ML predicted INSERT_RBRACKET"),)

    if label == CorrectionClass.INSERT_RBRACE.value:
        # Append one brace only if the delimiter tracker indicates an open block.
        if source.count("{") > source.count("}"):
            insert_at = offset if offset <= len(source) else len(source)
            return (_candidate(source, diagnostic.diagnostic_id, CorrectionAction.INSERT,
                "RBRACE", None, insert_at, insert_at, "}", grammar, "ML predicted INSERT_RBRACE"),)

    if label == CorrectionClass.DELETE_EXTRA_TOKEN.value and lexeme and end > offset:
        return (_candidate(source, diagnostic.diagnostic_id, CorrectionAction.DELETE,
            diagnostic.unexpected_token or "UNKNOWN", lexeme, offset, end, "", grammar,
            "ML predicted DELETE_EXTRA_TOKEN"),)

    if label == CorrectionClass.REPLACE_BRACKET.value:
        replacements = {("RBRACKET", "RPAREN"): ")", ("RPAREN", "RBRACKET"): "]",
                        ("LBRACKET", "LPAREN"): "(", ("LPAREN", "LBRACKET"): "["}
        target = next((text for (unexpected, wanted), text in replacements.items()
                       if diagnostic.unexpected_token == unexpected and wanted in expected), None)
        if target is not None and end > offset:
            target_type = {"[": "LBRACKET", "]": "RBRACKET", "(": "LPAREN", ")": "RPAREN"}[target]
            return (_candidate(source, diagnostic.diagnostic_id, CorrectionAction.REPLACE,
                target_type, lexeme, offset, end, target, grammar, "ML predicted REPLACE_BRACKET"),)

    if label == CorrectionClass.REPLACE_OPERATOR.value:
        # Common transposition of a two-character comparison operator.
        for bad, good, token_type in (("=>", ">=", "GE"), ("=<", "<=", "LE"),
                                      ("==>", "==", "EQ"), ("=!", "!=", "NE")):
            start = source.find(bad, max(0, offset - 2), min(len(source), offset + 3))
            if start >= 0:
                return (_candidate(source, diagnostic.diagnostic_id, CorrectionAction.REPLACE,
                    token_type, bad, start, start + len(bad), good, grammar,
                    "ML predicted REPLACE_OPERATOR"),)

    if label == CorrectionClass.CORRECT_KEYWORD.value:
        from .feature_extraction import MINI_C_KEYWORDS, edit_distance
        token = context.current_token
        if token and token.type == "IDENTIFIER":
            ranked_keywords = sorted((edit_distance(token.lexeme.lower(), keyword), keyword)
                                     for keyword in MINI_C_KEYWORDS)
            if ranked_keywords and ranked_keywords[0][0] in (1, 2):
                nearest = ranked_keywords[0][0]
                tied = [word for distance, word in ranked_keywords if distance == nearest]
                if len(tied) == 1:
                    return (_candidate(source, diagnostic.diagnostic_id, CorrectionAction.REPLACE,
                        tied[0].upper(), token.lexeme, token.offset, token.offset + len(token.lexeme),
                        tied[0], grammar, "ML predicted CORRECT_KEYWORD"),)

    if label == CorrectionClass.ARRAY_DECLARATION_ERROR.value:
        open_offset = offset if lexeme == "(" else _declaration_open_paren(source, offset)
        if open_offset is not None:
            candidates.append(_candidate(source, diagnostic.diagnostic_id, CorrectionAction.REPLACE,
                "LBRACKET", "(", open_offset, open_offset + 1, "[", "declaration",
                "ML predicted ARRAY_DECLARATION_ERROR"))

    elif label == CorrectionClass.ARRAY_INDEX_ERROR.value:
        if lexeme == ")":
            candidates.append(_candidate(source, diagnostic.diagnostic_id, CorrectionAction.REPLACE,
                "RBRACKET", ")", offset, end, "]", "array_access", "ML predicted ARRAY_INDEX_ERROR"))
        elif lexeme == "]":
            open_offset = source.rfind("(", 0, offset)
            if open_offset >= 0 and re.search(r"\b[A-Za-z_]\w*\s*\([^;{}]*$", source[max(0, open_offset - 80):open_offset + 1]):
                candidates.append(_candidate(source, diagnostic.diagnostic_id, CorrectionAction.REPLACE,
                    "LBRACKET", "(", open_offset, open_offset + 1, "[", "array_access",
                    "ML predicted ARRAY_INDEX_ERROR"))

    elif label == CorrectionClass.DECLARATION_SEPARATOR_ERROR.value:
        match = re.search(r"\b(int|float|char|bool)\s+([A-Za-z_]\w*)\s*;\s*([A-Za-z_]\w*)\s*;", source)
        if match:
            first_semicolon = source.find(";", match.start(2), match.end(2) + 1)
            typ = match.group(1)
            candidates.append(_candidate(source, diagnostic.diagnostic_id, CorrectionAction.REPLACE,
                "SEMICOLON", ";", first_semicolon, first_semicolon + 1, ",", "declaration",
                "ML predicted DECLARATION_SEPARATOR_ERROR: combine declarations"))
            candidates.append(_candidate(source, diagnostic.diagnostic_id, CorrectionAction.REPLACE,
                "SEMICOLON", ";", first_semicolon, first_semicolon + 1, f"; {typ} ", "declaration",
                "ML predicted DECLARATION_SEPARATOR_ERROR: split declarations"))

    elif label == CorrectionClass.KEYBOARD_GREATER_THAN.value:
        # `a.b` in a control condition can be a missed Shift+period. When the
        # parser stopped earlier (for example at a top-level `if`), use the
        # source pattern to locate the actual dot instead of blindly editing
        # the first diagnostic token.
        match = re.search(r"\b(?:if|while|for)\s*\([^{}]*?([A-Za-z_]\w*)\.([A-Za-z_]\w*)", source)
        if match:
            dot_offset = match.start(2) - 1
            candidates.append(_candidate(source, diagnostic.diagnostic_id, CorrectionAction.REPLACE,
                "GT", ".", dot_offset, dot_offset + 1, ">", "if_condition", "ML predicted KEYBOARD_GREATER_THAN"))
        elif _inside_condition(source, offset):
            if lexeme == ".":
                before = source[offset - 1] if offset > 0 else ""
                after = source[end] if end < len(source) else ""
                if (before.isalnum() or before == "_") and (after.isalpha() or after == "_"):
                    candidates.append(_candidate(source, diagnostic.diagnostic_id, CorrectionAction.REPLACE,
                        "GT", ".", offset, end, ">", "if_condition", "ML predicted KEYBOARD_GREATER_THAN"))
            elif lexeme.startswith(".") and len(lexeme) > 1:
                candidates.append(_candidate(source, diagnostic.diagnostic_id, CorrectionAction.REPLACE,
                    "GT", lexeme, offset, end, "> " + lexeme[1:], "if_condition",
                    "ML predicted KEYBOARD_GREATER_THAN"))

    elif label == CorrectionClass.KEYBOARD_LESS_THAN.value:
        if lexeme == "," and _inside_condition(source, offset):
            candidates.append(_candidate(source, diagnostic.diagnostic_id, CorrectionAction.REPLACE,
                "LT", ",", offset, end, "<", "if_condition", "ML predicted KEYBOARD_LESS_THAN"))

    elif label == CorrectionClass.KEYBOARD_MULTIPLY.value:
        # When '*' was typed as the unshifted 8 key, target the first 8 in `x 8 8`.
        match = re.search(r"\b([A-Za-z_]\w*|\d+|\)|\])\s+(8)\s+(8)\b", source)
        if match:
            start, finish = match.span(2)
            candidates.append(_candidate(source, diagnostic.diagnostic_id, CorrectionAction.REPLACE,
                "TIMES", "8", start, finish, "*", "expression", "ML predicted KEYBOARD_MULTIPLY"))
        elif lexeme == "8":
            candidates.append(_candidate(source, diagnostic.diagnostic_id, CorrectionAction.REPLACE,
                "TIMES", "8", offset, end, "*", grammar, "ML predicted KEYBOARD_MULTIPLY"))

    elif label == CorrectionClass.KEYBOARD_ASSIGNMENT.value:
        if lexeme == "+" and re.search(r"\b(?:int|float|char|bool)\s+[A-Za-z_]\w*\s*\+", source[max(0, offset - 40):offset + 1]):
            candidates.append(_candidate(source, diagnostic.diagnostic_id, CorrectionAction.REPLACE,
                "ASSIGN", "+", offset, end, "=", "declaration", "ML predicted KEYBOARD_ASSIGNMENT"))

    elif label == CorrectionClass.KEYBOARD_SEMICOLON.value:
        colon_offset = offset if lexeme == ":" else source.find(":", max(0, offset - 80), min(len(source), offset + 80))
        if colon_offset >= 0 and source[colon_offset:colon_offset + 1] == ":":
            candidates.append(_candidate(source, diagnostic.diagnostic_id, CorrectionAction.REPLACE,
                "SEMICOLON", ":", colon_offset, colon_offset + 1, ";", grammar,
                "ML predicted KEYBOARD_SEMICOLON"))

    elif label == CorrectionClass.KEYBOARD_LPAREN.value:
        match = re.search(r"\bif\s+9(?=[A-Za-z_]\w*)", source)
        if match:
            start = match.end() - 1
            candidates.append(_candidate(source, diagnostic.diagnostic_id, CorrectionAction.REPLACE,
                "LPAREN", "9", start, start + 1, "(", "if_condition", "ML predicted KEYBOARD_LPAREN"))

    elif label == CorrectionClass.KEYBOARD_RPAREN.value:
        # If a control condition reaches its body brace with unmatched opening
        # parentheses, preserve the expression and insert the missing closer.
        # This is safer than deleting a trailing digit: `x > 50 {` may mean
        # `x > 50)`, not `x > 5)`.
        brace = source.find("{", max(0, offset - 2), min(len(source), offset + 120))
        missing_closer = False
        if brace >= 0:
            prefix = source[:brace]
            control = list(re.finditer(r"\b(?:if|while|for)\s*\(", prefix))
            if control:
                opening = control[-1].end() - 1
                segment = source[opening:brace]
                balance = segment.count("(") - segment.count(")")
                if balance > 0 and "]" not in segment and "}" not in segment:
                    # When ML strongly predicts the learned Shift+0 class and
                    # the condition ends in a doubled numeric zero (the generated
                    # corruption for `...0)` -> `...00 {`), restore the delimiter
                    # at the last zero. For low-confidence cases such as `...50 {`,
                    # preserve the literal and insert the missing close paren.
                    trailing_zero = re.search(r"00\s*$", segment)
                    if trailing_zero and prediction.confidence >= 0.75:
                        cleaned = trailing_zero.group(0).rstrip()
                        start = opening + trailing_zero.start() + len(cleaned) - 1
                        candidates.append(_candidate(source, diagnostic.diagnostic_id,
                            CorrectionAction.REPLACE, "RPAREN", "0", start, start + 1,
                            ")", "if_condition", "ML predicted KEYBOARD_RPAREN"))
                    else:
                        insert_at = brace
                        while insert_at > opening and source[insert_at - 1].isspace():
                            insert_at -= 1
                        candidates.append(_candidate(source, diagnostic.diagnostic_id,
                            CorrectionAction.INSERT, "RPAREN", None, insert_at, insert_at,
                            ")" * balance, "if_condition",
                            "ML predicted KEYBOARD_RPAREN; insert missing condition closer"))
                    missing_closer = True

        # No unmatched condition closer was found: handle the narrower keyboard
        # substitution pattern in an otherwise complete control header.
        if not missing_closer:
            match = re.search(r"\b(?:if|while)\s*\([^{};]*?(\d)0(?=\s*[\{)])", source)
            if match:
                start = match.end() - 1
                candidates.append(_candidate(source, diagnostic.diagnostic_id, CorrectionAction.REPLACE,
                    "RPAREN", "0", start, start + 1, ")", "if_condition", "ML predicted KEYBOARD_RPAREN"))

    return tuple(candidates)
