"""Conservative review policy for compiler-validated correction candidates."""

from dataclasses import asdict, dataclass

from compiler.correction import CandidateValidation, CorrectionAction, CorrectionCandidate
from compiler.lexer import tokenize


@dataclass(frozen=True, slots=True)
class RepairSafety:
    category: str
    reason: str

    @property
    def requires_review(self) -> bool:
        return self.category != "LOW_RISK_STRUCTURAL"

    def to_dict(self) -> dict[str, str | bool]:
        return {**asdict(self), "requires_review": self.requires_review}


def assess_repair(
    candidate: CorrectionCandidate | None,
    validation: CandidateValidation | None,
    *,
    ambiguous: bool = False,
) -> RepairSafety:
    if ambiguous:
        return RepairSafety("AMBIGUOUS", "Multiple distinct repairs pass compiler checks.")
    if validation is None or not validation.relevant_valid:
        return RepairSafety("UNVERIFIED", "The compiler has not verified that the edit resolves its target.")
    if candidate is None or candidate.action != CorrectionAction.INSERT:
        return RepairSafety("POTENTIALLY_BEHAVIOR_CHANGING", "This edit can change tokens, bindings, or program structure.")
    delimiter = candidate.text.strip()
    if delimiter not in {";", ")", "]", "}"}:
        return RepairSafety("POTENTIALLY_BEHAVIOR_CHANGING", "The edit does not insert a single supported delimiter.")

    tokens, errors = tokenize(validation.corrected_source)
    start = candidate.offset + len(candidate.text) - len(candidate.text.lstrip())
    position = next(
        (i for i, token in enumerate(tokens) if token.offset == start and token.lexeme == delimiter),
        None,
    )
    if position is None or any(error.span.start.offset <= start for error in errors):
        return RepairSafety("UNVERIFIED", "The insertion does not resolve to a standalone delimiter at a clear token boundary.")

    before = [token.type for token in tokens[:position]]
    following = tokens[position + 1].type if position + 1 < len(tokens) else None
    control = {"IF", "WHILE", "FOR"}
    if delimiter == ";":
        open_parens = _unmatched_openers(before, "LPAREN", "RPAREN")
        finishes_control = (
            bool(before) and before[-1] == "RPAREN"
            and any(before[opener - 1] in control for opener in _unmatched_openers(before[:-1], "LPAREN", "RPAREN")[-1:] if opener)
        )
        allowed_next = {"RBRACE", "RETURN", "IF", "WHILE", "FOR", "BREAK", "CONTINUE", "INT", "FLOAT", "CHAR", "BOOL", "VOID"}
        if open_parens or finishes_control or following not in allowed_next:
            return RepairSafety("POTENTIALLY_BEHAVIOR_CHANGING", "This separator can change expression, statement, or control-flow boundaries.")
    elif delimiter == ")":
        open_parens = _unmatched_openers(before, "LPAREN", "RPAREN")
        if (following != "LBRACE" or not open_parens or not open_parens[-1]
                or before[open_parens[-1] - 1] not in control):
            return RepairSafety("POTENTIALLY_BEHAVIOR_CHANGING", "This closer can change grouping, arguments, or the controlled statement.")
    elif delimiter == "]":
        if (len(_unmatched_openers(before, "LBRACKET", "RBRACKET")) != 1
                or following not in {"SEMICOLON", "ASSIGN", "PLUS_ASSIGN", "MINUS_ASSIGN", "RPAREN", "RBRACE"}):
            return RepairSafety("POTENTIALLY_BEHAVIOR_CHANGING", "This closer can alter the index expression or how its value is used.")
    else:
        open_braces = _unmatched_openers(before, "LBRACE", "RBRACE")
        if (following is not None or errors or len(open_braces) != 1
                or "LBRACE" in before[open_braces[0] + 1:]):
            return RepairSafety("POTENTIALLY_BEHAVIOR_CHANGING", "This block closer can change which statements a scope contains.")

    return RepairSafety("LOW_RISK_STRUCTURAL", "A standalone delimiter matches a limited compiler-validated boundary.")


def _unmatched_openers(tokens: list[str], opener: str, closer: str) -> list[int]:
    pending = []
    for index, token in enumerate(tokens):
        if token == opener:
            pending.append(index)
        elif token == closer and pending:
            pending.pop()
    return pending


def repair_key(source: str) -> tuple[tuple[tuple[str, str], ...], tuple[str, ...]]:
    """Compare lexical structure while preserving literal text and lexical errors."""
    tokens, errors = tokenize(source)
    return tuple((token.type, token.lexeme) for token in tokens), tuple(error.lexeme for error in errors)
