"""Recommendation decisions use observed evidence and keep every patch review-only."""
from .intention_generalization import evidence_strength


def classify(candidate, *, ambiguous: bool):
    proposal = candidate.proposal
    if proposal.specification_matches:
        tier = "SPECIFICATION_SUPPORTED"
    elif any(fact.kind == "COMPILER_DIAGNOSTIC" for fact in proposal.evidence):
        tier = "COMPILER_CONFIRMED_ISSUE"
    elif evidence_strength(proposal):
        tier = "STRONG_CONTEXT"
    else:
        tier = "WEAK_CONTEXT"
    return {
        "tier": tier,
        "recommendation": "REVIEW_WITH_EVIDENCE" if candidate.compiler_valid and not ambiguous
        and tier != "WEAK_CONTEXT" else "ABSTAIN",
    }
