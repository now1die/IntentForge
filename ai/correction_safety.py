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
    if candidate is None or candidate.action != CorrectionAction.INSERT or candidate.text.strip() not in {";", ")", "]", "}"}:
        return RepairSafety("POTENTIALLY_BEHAVIOR_CHANGING", "This edit can change tokens, bindings, or program structure.")
    if candidate.text.strip() == ")" and candidate.grammar_context not in {"if_condition", "while_condition", "for_header"}:
        return RepairSafety("POTENTIALLY_BEHAVIOR_CHANGING", "A parenthesis here can change grouping or call arguments.")
    if candidate.text.strip() == "}" and validation.corrected_source[candidate.offset + len(candidate.text):].strip():
        return RepairSafety("POTENTIALLY_BEHAVIOR_CHANGING", "A block closer here can change the scope of later statements.")
    return RepairSafety("LOW_RISK_STRUCTURAL", "A localized missing delimiter was validated against the compiler diagnostic.")


def repair_key(source: str) -> tuple[tuple[tuple[str, str], ...], tuple[str, ...]]:
    """Compare lexical structure while preserving literal text and lexical errors."""
    tokens, errors = tokenize(source)
    return tuple((token.type, token.lexeme) for token in tokens), tuple(error.lexeme for error in errors)
