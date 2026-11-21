"""Read-only Phase 2 intention analysis and reviewable repairs."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from hashlib import sha256
from itertools import islice
from math import isfinite
from time import monotonic
from typing import Any

from compiler.ast_nodes import BinaryExpression, Identifier, ReturnStatement, VariableDeclaration
from analysis_evidence.function_summary import analyze_program, summaries
from compiler.semantic_analyzer import analyze_source_semantics
from compiler.symbol_table import SymbolKind

from .behavior_oracle import BehaviorResult, Status, Vector, program_identity
from .intention_phase35 import phase35_features, phase35_hypotheses
from .intention_phase5 import scan as phase5_scan
from .intention_phase55 import RULES as PRECISION_RULES, apply_precision_gates
from .intention_phase6 import proposals as semantic_proposals
from .intention_phase65 import COMPONENTS as PHASE65_COMPONENTS, augment as interprocedural_proposals
from .intention_phase75 import CATEGORIES as PHASE75_CATEGORIES, COMPONENTS as PHASE75_COMPONENTS
from .intention_phase9 import CATEGORIES as PHASE9_CATEGORIES, COMPONENTS as PHASE9_COMPONENTS, synthesize as robust_repairs
from .intention_phase85 import CATEGORIES as PHASE85_CATEGORIES, COMPONENTS as PHASE85_COMPONENTS, synthesize as finite_repairs
from .intention_phase8 import CATEGORIES as PHASE8_CATEGORIES, COMPONENTS as PHASE8_COMPONENTS, synthesize as arithmetic_repairs
from .specification import specification
from .intention_uncertainty import classify
from .correction_safety import RepairSafety, repair_key
from .intention_candidates import (MAX_CANDIDATES, Evidence, Proposal, apply_edits, candidate_stream,
                                   compiler_proposals, requirement_proposals)
from .intention_generalization import duplicate_guards, evidence_strength, generalized_features, hypotheses
from .intention_learning import ExpandedRanker, contextual_features
from .intention_recovery import expanded_proposals
from .intention_context import ContextLimit, IntentionContext, Requirement, UnsupportedContext, build_context
from .intention_ranker import Ranker
from .intention_requirements import expression_key, resolve_targets


DEFAULT_BUDGET_SECONDS = 1.5


@dataclass(slots=True)
class Candidate:
    id: str
    proposed_code: str
    proposal: Proposal
    compiler_valid: bool
    remaining_diagnostics: int
    features: dict[str, Any]
    relative_score: float | None = None
    ast_key: str | None = None
    behavior: BehaviorResult | None = None

    def to_dict(self, source: str, ambiguous: bool, evidence_policy: bool = False):
        safety = RepairSafety(
            "UNVERIFIED" if not self.compiler_valid else
            "AMBIGUOUS" if ambiguous else "POTENTIALLY_BEHAVIOR_CHANGING",
            "Compiler diagnostics remain. Continue editing before applying." if not self.compiler_valid else
            "Intention alternatives require explicit approval because the edit may change behavior.",
        )
        return {
            "id": self.id, "category": self.proposal.category,
            "proposed_code": self.proposed_code, "compiler_valid": self.compiler_valid,
            "remaining_diagnostics": self.remaining_diagnostics,
            "behavioral_status": self.behavior.status.value if self.behavior else "ORACLE_UNAVAILABLE",
            **({"behavioral_evidence": self.behavior.model_dump(mode="json", exclude={"execution"} if self.behavior.execution is None else None)} if self.behavior else {}),
            **(classify(self, ambiguous=ambiguous) if evidence_policy else {}),
            "relative_score": round(self.relative_score, 6) if self.relative_score is not None else None,
            "safety": safety.to_dict(),
            "hypothesis": self.proposal.assumption,
            "evidence": [fact.to_dict() for fact in self.proposal.evidence],
            "edits": [{
                "span": edit.span.to_dict(), "original": source[edit.span.start.offset:edit.span.end.offset],
                "proposed": edit.replacement,
            } for edit in self.proposal.edits],
        }


@dataclass(slots=True)
class IntentionResult:
    context: IntentionContext
    finding: str
    decision: str
    ranking: str
    candidates: list[Candidate]
    notes: list[str]
    evidence: tuple[Evidence, ...] = ()
    attempts: int = 0
    requirement_status: str | None = None
    candidate_ms: float = 0.0
    evidence_policy: bool = False
    behavior: BehaviorResult | None = None
    structural_scan: dict | None = None
    program_analysis: dict | None = None

    def record_behavior(self, result: BehaviorResult) -> None:
        """Accept evidence only from a caller that owns a trusted executor."""
        result = BehaviorResult.model_validate(result.model_dump())
        requirement = self.context.requirement
        if not requirement or result.entry_point != requirement.function or not requirement.examples:
            raise ValueError("Behavior requires the selected entry point and supplied examples.")
        vectors = tuple(Vector(arguments=item.args, expected=item.expected_return) for item in requirement.examples)
        if result.execution and tuple(row.model_dump_json() for row in result.execution.vectors) != tuple(
            row.model_dump_json() for row in vectors
        ):
            raise ValueError("Execution must correspond to the exact supplied vectors.")
        checked = tuple(row.vector for row in result.observations)
        if (tuple(row.model_dump_json() for row in checked)
                != tuple(row.model_dump_json() for row in vectors[:len(checked)])
                or result.status == Status.MATCHES_SUPPLIED_TESTS and len(checked) != len(vectors)):
            raise ValueError("Behavior observations must correspond to the supplied examples.")
        if result.candidate_id is None:
            if result.program != program_identity(self.context.source) or not self.context.compiler_valid:
                raise ValueError("Behavior mismatches the original program snapshot.")
            self.behavior = result
        else:
            choice = next((item for item in self.candidates if item.id == result.candidate_id), None)
            if not choice or not choice.compiler_valid or result.program != program_identity(choice.proposed_code):
                raise ValueError("Behavior mismatches the candidate snapshot.")
            choice.behavior = result

    def to_dict(self, *, include_context=False):
        ambiguous = self.decision == "AMBIGUOUS"
        candidates = [item.to_dict(self.context.source, ambiguous, self.evidence_policy) for item in self.candidates]
        if self.program_analysis is not None:
            for row, item in zip(candidates, self.candidates, strict=True):
                row.update(source_snapshot=program_identity(self.context.source),
                           analysis_completeness=self.program_analysis["status"],
                           counter_evidence=[fact.to_dict() for fact in item.proposal.counter_evidence],
                           requires_approval=True)
                if "phase65" in self.program_analysis:
                    facts = {fact.kind for fact in item.proposal.evidence}
                    row["evidence_basis"] = ("supplied_specification" if item.proposal.specification_matches else
                        "supplied_examples" if facts & {"PATH_TEST_DOMAIN", "SUPPLIED_RECURSIVE_TEST",
                                                        "SUPPLIED_DOMAIN_POINT", "SUPPLIED_BASE_RESULT",
                                                        "MULTIPLE_RECURSIVE_EXAMPLES", "LEXICAL_RECURSIVE_TERMS",
                                                        "MISSING_INPUT_DEPENDENCY", "INCONSISTENT_LOOP_RADIX",
                                                        "ARITHMETIC_CONSTRAINT_WITNESS", "FINITE_CONSTRAINT_WITNESS"} else "static")
                    row["hypothesis_origin"] = ("phase9" if item.proposal.category in PHASE9_CATEGORIES else
                                                "phase85" if item.proposal.category in PHASE85_CATEGORIES else
                                                "phase8" if item.proposal.category in PHASE8_CATEGORIES else
                                                "phase75" if item.proposal.category in PHASE75_CATEGORIES else "phase65" if item.proposal.category in {
                        "RECURSIVE_PARAMETER_PROGRESS", "RECURRENCE_OPERATOR_MISMATCH", "PATH_RETURN_DEPENDENCY"}
                        else "earlier_engine")
        return {
            "finding": self.finding, "decision": self.decision, "ranking": self.ranking,
            "compiler_valid": self.context.compiler_valid,
            "behavioral_status": self.behavior.status.value if self.behavior else
            "EXECUTION_UNSUPPORTED" if self.finding == "UNSUPPORTED_LANGUAGE" else "ORACLE_UNAVAILABLE",
            **({"behavioral_evidence": self.behavior.model_dump(mode="json", exclude={"execution"} if self.behavior.execution is None else None)} if self.behavior else {}),
            **({"recommendation": candidates[0]["recommendation"] if candidates else "ABSTAIN"} if self.evidence_policy else {}),
            "diagnostics": [item.to_dict() for item in self.context.diagnostics],
            "evidence": [fact.to_dict() for fact in self.evidence],
            "notes": self.notes, "attempts": self.attempts,
            **({"requirement_status": self.requirement_status} if self.requirement_status else {}),
            **({"structural_scan": self.structural_scan} if self.structural_scan is not None else {}),
            **({"program_analysis": self.program_analysis} if self.program_analysis is not None else {}),
            "candidates": candidates,
            "context": self.context.to_dict() if include_context else None,
        }


def candidate_features(context, proposal, remaining):
    pairs = [(context.text(edit.span), edit.replacement.strip()) for edit in proposal.edits]
    return {
        "node_shape": proposal.node_kind, "ast_edge": proposal.role,
        "binding_kind": proposal.symbol_kind,
        "type_agrees": int(proposal.type_match),
        "declaration_distance": min(proposal.symbol_distance, 512) / 512,
        "prior_binding_uses": min(proposal.references_before, 10),
        "identifier_similarity": max(SequenceMatcher(None, old, new, autojunk=False).ratio() for old, new in pairs),
        "edit_size": min(sum(abs(len(old) - len(new)) for old, new in pairs), 100) / 100,
        "edit_count": len(proposal.edits),
        "has_requirement_support": int(proposal.specification_matches > 0),
        "diagnostics_removed": min(len(context.diagnostics) - remaining, MAX_CANDIDATES),
        "diagnostics_remaining": min(remaining, MAX_CANDIDATES),
    }


def order_candidates(candidates: list[Candidate], ranker: Ranker | None, *, expanded=None, experimental=None, deadline=None, generalized=False):
    """Keep validated and directly specified candidates ahead of other hypotheses."""
    groups = defaultdict(list)
    for candidate in candidates:
        candidate.relative_score = None
        groups[(not candidate.compiler_valid, -candidate.proposal.specification_matches,
                candidate.remaining_diagnostics)].append(candidate)

    result = []
    for key in sorted(groups):
        group = groups[key]
        # Deployment evidence covers competing visible bindings in return-value positions.
        compatible = all(item.proposal.node_kind == "Identifier" and item.proposal.in_return_position
                         and item.proposal.symbol_kind in {"variable", "parameter"} for item in group)
        if ranker and compatible and len(group) > 1:
            for candidate, score in zip(group, ranker.score([item.features for item in group]), strict=True):
                if not isfinite(score):
                    raise ValueError("Ranker returned a non-finite score")
                candidate.relative_score = score
        ordered = sorted(group, key=lambda item: (
            -int(generalized and evidence_strength(item.proposal)),
            -(item.relative_score if item.relative_score is not None else item.features["identifier_similarity"]),
            not item.proposal.type_match, item.proposal.symbol_distance, item.id,
        ))
        if expanded:
            if deadline is not None and monotonic() >= deadline:
                raise TimeoutError("Ranker budget expired")
            ordered = expanded.order(ordered, experimental=experimental, deadline=deadline)
        result.extend(ordered)
    return result


def _unsupported(context: IntentionContext) -> bool:
    if context.parsed.valid:
        return False
    tokens = [token.lexeme for token in context.parsed.tokens]
    if any(err.lexeme in {"#", "?"} for err in context.parsed.lexical_errors):
        return True
    for first, second, third in zip(tokens, tokens[1:], tokens[2:]):
        if ((first, second) in {("switch", "("), ("do", "{")}
                or (first in {"struct", "union", "enum"} and third == "{")
                or (first in {"int", "char", "float", "void", "bool"} and second == "*")
                or (first == "]" and second == "[")):
            return True
    return False


def _heuristic(context: IntentionContext) -> tuple[Evidence, ...]:
    if context.requirement:
        return ()
    for record in context.nodes:
        node = record.node
        function = record.function
        if not isinstance(node, ReturnStatement) or not isinstance(node.value, Identifier) or not function:
            continue
        if len(function.body.statements) != 2 or function.body.statements[-1] is not node:
            continue
        declaration = function.body.statements[0]
        binding = context.visible_at(node.value.span.start.offset).get(node.value.name)
        if not binding or binding.kind != SymbolKind.PARAMETER:
            continue
        if (isinstance(declaration, VariableDeclaration) and isinstance(declaration.initializer, BinaryExpression)
                and declaration.type_name == function.return_type):
            return (
                Evidence("OBSERVED_AST", f"{declaration.name} is computed in the immediately preceding declaration.", declaration.span),
                Evidence("SYMBOL", f"The function returns parameter {binding.name} instead of referencing that declaration.", node.value.span),
            )
    return ()


def _validate_candidate(context, proposal, *, enhanced=False, generalized=False, phase35=False):
    try:
        fixed = apply_edits(context.source, proposal.edits)
    except ValueError:
        return None
    if fixed == context.source or len(fixed) > len(context.source) + 320:
        return None
    checked = analyze_source_semantics(fixed)
    remaining = len(checked.parse_result.lexical_errors) + len(checked.parse_result.syntax_errors)
    if checked.semantic_result:
        remaining += len(checked.semantic_result.diagnostics)
    if not checked.success and (not checked.parse_result.valid or remaining >= len(context.diagnostics)):
        return None
    if proposal.specification_matches:
        # A replacement must really match the specified AST after parsing the patched program.
        new_targets, _ = resolve_targets(build_context(fixed, context.requirement), enhanced=enhanced, generalized=generalized)
        old_targets, _ = resolve_targets(context, enhanced=enhanced, generalized=generalized)
        if sum(target.matches for target in new_targets) < sum(target.matches for target in old_targets) + proposal.specification_matches:
            return None
    features = candidate_features(context, proposal, remaining)
    if enhanced:
        features.update(contextual_features(context, proposal))
    ast_key = None
    if generalized:
        features.update(generalized_features(context, proposal))
        if phase35:
            features.update(phase35_features(context, proposal))
        if checked.parse_result.ast is not None:
            ast_key = repr(expression_key(checked.parse_result.ast))
    return Candidate("IR-" + sha256(fixed.encode()).hexdigest()[:12], fixed, proposal, checked.success,
                     remaining, features, ast_key=ast_key)


def analyze_intention(
    source: str, requirement: Requirement | None = None, *, ranker: Ranker | None = None,
    ranking_status: str = "DETERMINISTIC", budget_seconds: float = DEFAULT_BUDGET_SECONDS,
    candidate_budget: int = MAX_CANDIDATES, enhanced: bool = False,
    expanded_ranker: ExpandedRanker | None = None, experimental: str | None = None,
    generalized: bool = False, generation_v3: bool = True, phase35: bool = False,
    phase5: bool = False, phase5_generate: bool = True,
    phase55: bool = False, phase55_rules: frozenset[str] = PRECISION_RULES,
    phase6: bool = False, phase6_generate: bool = True, phase6_graph: bool = False,
    phase6_entry: str | None = None, phase6_examples=(),
    phase65: bool = False, phase65_components: frozenset[str] = PHASE65_COMPONENTS,
    phase7: bool = False, phase7_components: frozenset[str] = frozenset({"layout", "helpers"}),
    phase75: bool = False, phase75_components: frozenset[str] = PHASE75_COMPONENTS,
    phase8: bool = False, phase8_components: frozenset[str] = PHASE8_COMPONENTS,
    phase8_domain=None, phase8_partial=(),
    phase85: bool = False, phase85_components: frozenset[str] = PHASE85_COMPONENTS,
    phase9: bool = False, phase9_components: frozenset[str] = PHASE9_COMPONENTS,
) -> IntentionResult:
    phase85 = phase85 or phase9
    phase8 = phase8 or phase85
    phase75 = phase75 or phase8
    phase7 = phase7 or phase75
    phase65 = phase65 or phase7
    phase6 = phase6 or phase65
    phase55 = phase55 or phase6
    phase5 = phase5 or phase55
    phase35 = phase35 or phase5
    generalized = generalized or phase35
    enhanced = enhanced or generalized
    deadline = monotonic() + budget_seconds
    try:
        context = build_context(source, requirement)
    except TypeError as exc:
        if phase6 and str(exc) == "Cannot obtain source span for list":
            raise UnsupportedContext("Wrap control-body declarations in a block for Phase 6 analysis.") from exc
        raise
    if _unsupported(context):
        return IntentionResult(context, "UNSUPPORTED_LANGUAGE", "NO_SUPPORTED_CORRECTION", ranking_status, [],
                               ["The source contains syntax outside the supported Mini-C subset."],
                               structural_scan={"status": "INCOMPLETE_COMPILER_EVIDENCE", "findings": []}
                               if phase5 and requirement is None else None,
                               program_analysis={"status": "INCOMPLETE_COMPILER_EVIDENCE", "functions": [], "hypotheses": []}
                               if phase6 else None)
    targets, notes = resolve_targets(context, enhanced=enhanced, generalized=generalized)
    mismatches = [target for target in targets if not target.matches]
    heuristic = _heuristic(context) if not enhanced and context.compiler_valid and not mismatches else ()
    if generalized and generation_v3 and context.compiler_valid and requirement is None:
        heuristic = duplicate_guards(context)
    finding = ("COMPILER_ERROR" if not context.compiler_valid else "SPECIFICATION_SUPPORTED_SUSPICION" if mismatches
               else "HEURISTIC_SUSPICION" if heuristic else "NO_SUPPORTED_MISMATCH")
    evidence = heuristic or tuple(Evidence(
        "USER_REQUIREMENT",
        f"The selected {target.field} differs structurally from "
        f"{'the interpreted requirement' if target.derived_from_description else 'the supplied expression'} {target.expected_source!r}.",
        target.observed.span if target.observed is not None else target.record.node.span,
    ) for target in mismatches)
    if heuristic and generalized:
        notes.append("Duplicate guards can be deliberate redundancy. The intended alternative is unspecified.")
    elif heuristic:
        notes.append("The computed value could be intentional or unused. Provide a requirement before proposing a logic edit.")
    started_generation = monotonic()
    scan_status, discovered = phase5_scan(context, deadline, normalize=phase6) if phase5 and requirement is None else (None, ())
    structural = None
    withheld = ()
    if phase55 and discovered:
        discovered, withheld, limited = apply_precision_gates(context, discovered, deadline, phase55_rules)
        if limited:
            scan_status = "SCAN_LIMITED"
    if scan_status:
        structural = {"status": scan_status, "findings": [
            {"category": proposal.category, "assumption": proposal.assumption,
             "evidence": [item.to_dict() for item in proposal.evidence]} for proposal in discovered
        ]}
        if phase55:
            structural["withheld"] = [
                {"category": proposal.category, "assumption": proposal.assumption,
                 "evidence": [fact.to_dict() for fact in proposal.evidence], "counter_evidence": reason.to_dict()}
                for proposal, reason in withheld
            ]
    semantic = ()
    program_analysis = None
    if phase6:
        program = analyze_program(context, deadline)
        examples = requirement.examples if requirement and not phase6_examples else phase6_examples
        entry = phase6_entry or (requirement.function if requirement else None)
        spec = specification(context, entry, examples, phase8_domain, phase8_partial) if phase8 else None
        if entry is None:
            examples = ()
        elif spec is not None:
            examples = spec.examples
        semantic = semantic_proposals(context, program, entry, examples)
        extended = None
        if phase65:
            semantic, extended = interprocedural_proposals(
                context, program, semantic, entry, examples,
                phase65_components | (phase7_components if phase7 else frozenset()),
                phase75=phase75_components if phase75 else None,
            )
        program_analysis = summaries(context, program, include_graph=phase6_graph)
        if extended is not None:
            program_analysis["phase65"] = extended
            if program_analysis["status"] == "AVAILABLE":
                program_analysis["status"] = extended["status"]
        if spec is not None:
            links = extended["interprocedural"] if extended else {}
            helper_shapes = {name: item["scalar_helper"] for name, item in links.items() if "scalar_helper" in item}
            arithmetic, constraints = arithmetic_repairs(context, program, links, helper_shapes, spec, phase8_components)
            semantic = (*arithmetic, *semantic)
            program_analysis["phase8"] = {"specification": spec.summary(), "constraints": constraints}
            if phase85:
                finite, report = finite_repairs(context, program, links, helper_shapes, spec, phase85_components)
                semantic = (*finite, *semantic)
                program_analysis["phase85"] = report
            if phase9:
                robust, report = robust_repairs(context, program, links, helper_shapes, spec, phase9_components)
                semantic = (*robust, *semantic)
                program_analysis["phase9"] = report
        program_analysis["hypotheses"] = [{"category": proposal.category, "assumption": proposal.assumption,
                                            "evidence": [fact.to_dict() for fact in proposal.evidence],
                                            "counter_evidence": [fact.to_dict() for fact in proposal.counter_evidence]}
                                           for proposal in semantic]
    if (semantic or discovered) and finding == "NO_SUPPORTED_MISMATCH":
        finding = "HEURISTIC_SUSPICION"
        evidence = (semantic or discovered)[0].evidence
        notes.append("Analysis found a plausible inconsistency. Programmer intent remains unknown." if phase6 else
                     "The structural scan found a plausible inconsistency. Programmer intent remains unknown.")
    if enhanced:
        def stream():
            yield from requirement_proposals(context, targets)
            if phase6_generate:
                yield from semantic
            if phase5_generate:
                yield from discovered
            if phase35 and requirement is None:
                yield from phase35_hypotheses(context)
            if generalized and generation_v3:
                yield from islice(hypotheses(context, allow_logic=requirement is None), 8)
            yield from expanded_proposals(context, compiler_proposals(context),
                                          allow_heuristics=requirement is None and not (generalized and generation_v3))
        source_proposals = stream()
    else:
        source_proposals = candidate_stream(context, targets)
    proposals = islice(source_proposals, max(0, min(candidate_budget, MAX_CANDIDATES)))
    unique = {}
    attempted_edits = set()
    candidates = []
    attempts = 0
    timed_out = monotonic() >= deadline
    if not timed_out:
        for proposal in proposals:
            if monotonic() >= deadline:
                timed_out = True
                break
            signature = tuple((edit.span.start.offset, edit.span.end.offset, edit.replacement) for edit in proposal.edits)
            if signature in attempted_edits:
                continue
            attempted_edits.add(signature)
            attempts += 1
            try:
                candidate = _validate_candidate(context, proposal, enhanced=enhanced, generalized=generalized, phase35=phase35)
            except (ContextLimit, RecursionError):
                continue
            if monotonic() >= deadline:
                timed_out = True
                break
            if candidate and (not phase6 or candidate.compiler_valid):
                key = candidate.ast_key or repair_key(candidate.proposed_code)
                if key not in unique:
                    unique[key] = len(candidates)
                    candidates.append(candidate)
                elif enhanced:
                    index = unique[key]
                    previous = candidates[index].proposal
                    if ((candidate.proposal.specification_matches,
                         generalized and evidence_strength(candidate.proposal), -len(candidate.proposal.edits))
                            > (previous.specification_matches,
                               generalized and evidence_strength(previous), -len(previous.edits))):
                        candidates[index] = candidate
    candidate_ms = (monotonic() - started_generation) * 1000
    if enhanced and context.compiler_valid and not mismatches and candidates:
        finding = "HEURISTIC_SUSPICION"
        evidence = candidates[0].proposal.evidence
        if generalized:
            notes.append("A boundary or peer pattern suggests an alternative. Deliberate asymmetry is possible.")
            if phase7 and (phase6_examples or requirement and requirement.examples):
                notes.append("Supplied examples guide synthesis. Isolated verification observes program behavior.")
            else:
                notes.append("No behavior specification was supplied. Compilation verifies syntax and types only.")
        else:
            notes.append("Context supports review of these alternatives. Programmer intent remains uncertain.")
    try:
        candidates = order_candidates(candidates, ranker, expanded=expanded_ranker, experimental=experimental,
                                      deadline=deadline if expanded_ranker else None, generalized=generalized)
    except (ValueError, TypeError, AttributeError, RuntimeError, KeyError, TimeoutError) as exc:
        for candidate in candidates:
            candidate.relative_score = None
        timed_out = timed_out or isinstance(exc, TimeoutError)
        ranking_status = "RANKING_BUDGET_EXHAUSTED" if timed_out else "ARTIFACT_INCOMPATIBLE"
        candidates = order_candidates(candidates, None, generalized=generalized)
    if ranking_status == "LEARNED" and not any(candidate.relative_score is not None for candidate in candidates):
        ranking_status = "DETERMINISTIC_OUTSIDE_MODEL_SCOPE"
    if ranking_status in {"EXPANDED_LEARNED", "V3_LEARNED", "V4_LEARNED"} and not any(candidate.relative_score is not None for candidate in candidates):
        ranking_status = "DETERMINISTIC_OUTSIDE_MODEL_SCOPE"
    if generalized and candidates and finding == "HEURISTIC_SUSPICION":
        evidence = candidates[0].proposal.evidence
    if timed_out:
        notes.append("The analysis budget expired. Only completed checks are shown.")
        decision = "BUDGET_EXHAUSTED"
    elif (candidates and candidates[0].compiler_valid and candidates[0].proposal.specification_matches
          and candidates[0].proposal.specification_matches == len(mismatches)
          and not any("no unique location" in note for note in notes)):
        decision = "STRONG_SPECIFICATION_EVIDENCE"
    elif len(candidates) > 1:
        decision = "AMBIGUOUS"
    elif candidates:
        decision = "REVIEW_UNCERTAIN"
    elif notes or heuristic or mismatches:
        decision = "INSUFFICIENT_CONTEXT"
    elif context.compiler_valid and targets and all(target.matches for target in targets):
        decision = "REQUIREMENT_SHAPE_MATCHES"
    else:
        decision = "NO_SUPPORTED_CORRECTION"
    requirement_status = None
    if enhanced:
        if not requirement:
            requirement_status = "CODE_ONLY"
        elif targets:
            requirement_status = "SUPPORTED"
        elif any("description is recorded" in note for note in notes):
            requirement_status = "UNSUPPORTED_DESCRIPTION"
        else:
            requirement_status = "UNRESOLVED"
        if requirement_status == "UNSUPPORTED_DESCRIPTION":
            decision = "INSUFFICIENT_CONTEXT"
    return IntentionResult(context, finding, decision, ranking_status, candidates, notes, evidence, attempts,
                           requirement_status, candidate_ms, evidence_policy=phase35, structural_scan=structural,
                           program_analysis=program_analysis)
