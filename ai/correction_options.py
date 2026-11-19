"""Interactive correction options: generate, validate and rank multiple repairs."""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from compiler.correction import CorrectionCandidate, CandidateValidation, apply_candidate, validate_candidate
from compiler.parser import parse
from compiler.semantic_analyzer import analyze_source_semantics
from compiler.errors import SyntaxDiagnostic
from compiler.source_location import SourceLocation, SourceSpan

from .candidate_ranker import rank_candidates
from .correction_safety import RepairSafety, assess_repair, repair_key
from compiler.compound_recovery import generate_compound_candidates
from .error_context import ErrorContext
from .error_predictor import MLCorrectionPredictor
from .ml_candidate_generator import generate_ml_candidates
from .llm_fallback import OllamaFallbackService


def _dedupe(candidates: list[CorrectionCandidate]) -> list[CorrectionCandidate]:
    seen: set[tuple[Any, ...]] = set()
    result: list[CorrectionCandidate] = []
    for candidate in candidates:
        signature = (
            candidate.action.value,
            candidate.offset,
            candidate.span.end.offset,
            candidate.text,
            tuple((e.action.value, e.offset, e.span.end.offset, e.text) for e in candidate.edits),
        )
        if signature not in seen:
            seen.add(signature)
            result.append(candidate)
    return result


def _semantic_count(source: str) -> int:
    parsed = parse(source)
    if not parsed.valid:
        return 10_000
    result = analyze_source_semantics(source).semantic_result
    return len(result.diagnostics) if result is not None else 0


def _declaration_alternatives(source: str) -> list[str]:
    """Offer conservative alternatives for `int x; y` / `int x; y;`."""
    import re
    out: list[str] = []
    pattern = re.compile(r"\b(?P<type>int|float|char|bool)\s+(?P<a>[A-Za-z_]\w*)\s*;\s*(?P<b>[A-Za-z_]\w*)\s*(?P<tail>;|(?=\}))")
    for match in pattern.finditer(source):
        typ, a, b = match.group("type"), match.group("a"), match.group("b")
        tail = match.group("tail") or ""
        start, end = match.span()
        replacements = [
            f"{typ} {a}, {b};" + ("" if tail == ";" else ""),
            f"{typ} {a}; {typ} {b};" + ("" if tail == ";" else ""),
        ]
        for replacement in replacements:
            candidate = source[:start] + replacement + source[end:]
            parsed = parse(candidate)
            if parsed.valid and _semantic_count(candidate) < 10_000:
                out.append(candidate)
    return out


def _local_pattern_alternatives(source: str) -> list[dict[str, Any]]:
    """Return high-signal local repairs even when an unrelated earlier parser
    error prevents whole-program validation. These are deliberately labelled
    as local-progress suggestions, not fully compiler-valid programs.
    """
    import re
    out: list[dict[str, Any]] = []
    # Keyboard comparison: parser may stop at a top-level `if`, but the source
    # still contains an unambiguous missed Shift+period pattern.
    for match in re.finditer(r"\b(if|while|for)\s*\(([^{}]*?)\.([A-Za-z_]\w*)", source):
        dot = match.start(3) - 1
        corrected = source[:dot] + ">" + source[dot + 1:]
        if corrected != source:
            out.append({
                "id": f"LOCAL-GT-{len(out)+1:02d}", "label": "Local repair",
                "corrected_code": corrected, "score": 0.90, "confidence": 0.90,
                "predicted_class": "KEYBOARD_GREATER_THAN", "matched_class": "KEYBOARD_GREATER_THAN",
                "reason": "Local keyboard comparison repair; the surrounding source still needs to satisfy the Mini-C top-level grammar",
                "grammar_context": "if_condition", "candidate": None, "validation": None,
                "semantic_errors": None, "fully_valid": False, "origin": "local_pattern_fallback",
            })
    return out


def _semantic_array_call_alternatives(source: str) -> list[dict[str, Any]]:
    import re
    declarations = set(re.findall(r"\b(?:int|float|char|bool)\s+([A-Za-z_]\w*)\s*\[", source))
    out=[]
    for name in declarations:
        for match in re.finditer(rf"\b{re.escape(name)}\s*\(([^()]*)\)", source):
            open_at = source.find("(", match.start(), match.end())
            close_at = match.end()-1
            corrected = source[:open_at] + "[" + source[open_at+1:close_at] + "]" + source[close_at+1:]
            if corrected == source or not parse(corrected).valid:
                continue
            sem_count = _semantic_count(corrected)
            out.append({
                "id": f"ARRAY-SEM-{len(out)+1:02d}", "label": f"Option {len(out)+1}",
                "corrected_code": corrected, "score": 0.93, "confidence": 0.93,
                "predicted_class": "ARRAY_CALL_ERROR", "matched_class": "ARRAY_CALL_ERROR",
                "reason": "Array is declared with [] but used with (); convert the call-style access to indexing",
                "grammar_context": "array_access", "candidate": None, "validation": None,
                "semantic_errors": sem_count, "fully_valid": sem_count == 0, "origin": "semantic_contextual_alternative",
            })
    return out

def _contextual_scenario_alternatives(source: str) -> list[dict[str, Any]]:
    """Generate high-signal whole-program alternatives for interacting errors."""
    import re
    out: list[dict[str, Any]] = []

    # Scalar declaration later used with indexing. The declaration is changed to
    # the minimum array size required by a constant index, while preserving the access.
    m = re.search(r"\b(?P<typ>int|float|char|bool)\s+(?P<name>[A-Za-z_]\w*)\s*;", source)
    if m:
        typ, name = m.group("typ"), m.group("name")
        access = re.search(rf"\b{re.escape(name)}\s*(?P<open>[\[\{{\(])\s*(?P<idx>[A-Za-z0-9_+*/%.-]+)\s*(?P<close>[\]\}}\)])\s*=", source[m.end():])
        if access:
            idx = access.group("idx").strip()
            try:
                minimum = int(idx) + 1 if idx.isdigit() else None
            except ValueError:
                minimum = None
            if minimum is not None:
                corrected = re.sub(
                    rf"\b{re.escape(typ)}\s+{re.escape(name)}\s*;",
                    f"{typ} {name}[{minimum}];",
                    source,
                    count=1,
                )
                # Normalize the access delimiters in the corrected source.
                access_start = m.end() + access.start("open")
                # Find the corresponding delimiters in the already-modified source.
                open_at = corrected.find(access.group("open"), m.end())
                if open_at >= 0:
                    close_at = corrected.find(access.group("close"), open_at + 1)
                    if close_at > open_at:
                        corrected = corrected[:open_at] + "[" + corrected[open_at + 1:close_at] + "]" + corrected[close_at + 1:]
                if parse(corrected).valid and _semantic_count(corrected) == 0:
                    out.append({
                        "id": "SCALAR-ARRAY-01", "label": "Option", "corrected_code": corrected,
                        "score": 0.97, "confidence": 0.97, "predicted_class": "SCALAR_ARRAY_USE_ERROR",
                        "matched_class": "SCALAR_ARRAY_USE_ERROR",
                        "reason": f"Treat '{name}' as an array and preserve index {idx}; minimum size is {minimum}.",
                        "grammar_context": "array_access", "candidate": None, "validation": None,
                        "semantic_errors": 0, "fully_valid": True, "origin": "contextual_scenario"
                    })

    # Declaration punctuation: dot/colon are often intended as separators.
    m = re.search(r"\b(?P<typ>int|float|char|bool)\s+(?P<a>[A-Za-z_]\w*)\s*(?P<punct>[.:])\s*(?P<b>[A-Za-z_]\w*)\s*;", source)
    if m:
        typ, a, b, punct = m.group("typ"), m.group("a"), m.group("b"), m.group("punct")
        alternatives = [
            (f"{typ} {a}, {b};", "Treat the punctuation as a declaration separator."),
            (f"{typ} {a};\n{typ} {b};", "Split the declaration into two statements."),
        ]
        for idx, (replacement, reason) in enumerate(alternatives, 1):
            candidate = source[:m.start()] + replacement + source[m.end():]
            if parse(candidate).valid and _semantic_count(candidate) == 0:
                out.append({
                    "id": f"DECL-PUNCT-{idx:02d}", "label": "Option", "corrected_code": candidate,
                    "score": 0.95 - (idx-1)*0.04, "confidence": 0.95 - (idx-1)*0.04,
                    "predicted_class": "DECLARATION_DOT_ERROR" if punct == "." else "DECLARATION_COLON_ERROR",
                    "matched_class": "DECLARATION_PUNCTUATION", "reason": reason,
                    "grammar_context": "declaration", "candidate": None, "validation": None,
                    "semantic_errors": 0, "fully_valid": True, "origin": "contextual_scenario"
                })

    # Array already declared: normalize a mismatched brace index.
    m = re.search(r"\b(?P<name>[A-Za-z_]\w*)\s*\{(?P<idx>[^}]*)\]\s*=", source)
    if m:
        name = m.group("name")
        declaration = re.search(rf"\b(?:int|float|char|bool)\s+{re.escape(name)}\s*\[[^\]]+\]\s*;", source)
        if declaration:
            open_at = m.start() + m.group(0).find("{")
            close_at = source.find("]", open_at)
            if close_at > open_at:
                candidate = source[:open_at] + "[" + source[open_at + 1:close_at] + "]" + source[close_at + 1:]
                if parse(candidate).valid and _semantic_count(candidate) == 0:
                    out.append({
                        "id": "ARRAY-BRACE-01", "label": "Option", "corrected_code": candidate,
                        "score": 0.99, "confidence": 0.99, "predicted_class": "ARRAY_BRACE_INDEX_ERROR",
                        "matched_class": "ARRAY_BRACE_INDEX_ERROR",
                        "reason": "The identifier is declared as an array; replace the mismatched index delimiter with [].",
                        "grammar_context": "array_access", "candidate": None, "validation": None,
                        "semantic_errors": 0, "fully_valid": True, "origin": "contextual_scenario"
                    })
    return out


def _ollama_review_and_fallback(source: str, context: ErrorContext, prediction: Any, options: list[dict[str, Any]], limit: int, *, use_ollama: bool = True) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Verify compiler-valid options with local Ollama; generate fresh options only
    when the ML/compiler pipeline has none. Ollama never bypasses compiler validation."""
    meta = {"mode": "not_used", "approved_ids": []}
    _annotate_safety(options)
    if not use_ollama:
        return options[:limit], meta
    service = OllamaFallbackService()
    if options:
        review = service.review_candidates(source, context, [{"id": x["id"], "corrected_code": x["corrected_code"], "reason": x["reason"], "fully_valid": x["fully_valid"]} for x in options])
        meta.update(review.to_dict()); meta["mode"] = "verification"
        if review.attempted and review.approved_ids:
            approved = set(review.approved_ids)
            reviewed = [x for x in options if x["id"] in approved]
            if reviewed:
                for item in reviewed:
                    item["ollama_verified"] = True
                    item["ollama_score"] = (review.scores or {}).get(item["id"])
                return reviewed[:limit], meta
        return options[:limit], meta
    generated = service.generate_options(source, context, prediction)
    meta.update(generated.to_dict()); meta["mode"] = "generation_fallback"
    generated_options: list[dict[str, Any]] = []
    for idx, candidate_source in enumerate(generated.candidates, 1):
        parsed = parse(candidate_source)
        if not parsed.valid or _semantic_count(candidate_source) != 0 or candidate_source == source:
            continue
        generated_options.append({
            "id": f"OLLAMA-{idx:02d}", "label": f"Option {idx}", "corrected_code": candidate_source,
            "score": 0.70, "confidence": 0.70, "predicted_class": prediction.label,
            "matched_class": "OLLAMA_GENERATED", "reason": "Generated by local Ollama and independently compiler-validated.",
            "grammar_context": context.grammar_context or "unknown", "candidate": None, "validation": None,
            "semantic_errors": 0, "fully_valid": True, "origin": "ollama_fallback", "ollama_verified": True,
        })
    _annotate_safety(generated_options)
    return generated_options[:limit], meta

def _annotate_safety(options: list[dict[str, Any]]) -> None:
    viable = [item for item in options if item["fully_valid"]] or options
    ambiguous = len({repair_key(item["corrected_code"]) for item in viable}) > 1
    for item in options:
        if ambiguous:
            safety = assess_repair(None, None, ambiguous=True)
        elif item.get("safety"):
            continue
        elif item["fully_valid"]:
            safety = RepairSafety(
                "POTENTIALLY_BEHAVIOR_CHANGING", "This whole-source proposal may change bindings or behavior."
            )
        else:
            safety = assess_repair(None, None)
        item["safety"] = safety.to_dict()


def suggest_correction_options(source: str, predictor: MLCorrectionPredictor, limit: int = 8, *, use_ollama: bool = True) -> dict[str, Any]:
    baseline = parse(source)
    if baseline.valid:
        semantic = analyze_source_semantics(source).semantic_result
        semantic_errors = len(semantic.diagnostics) if semantic is not None else 0
        semantic_options = _semantic_array_call_alternatives(source) if semantic_errors else []
        declaration_alts = _declaration_alternatives(source) if semantic_errors else []
        semantic_prediction = None
        if semantic and semantic.diagnostics:
            sem = next((item for item in semantic.diagnostics if item.code == "SEM-NOT-CALLABLE"), semantic.diagnostics[0])
            semantic_offset = source.find("(", sem.span.end.offset, min(len(source), sem.span.end.offset + 8))
            if semantic_offset >= 0:
                span = SourceSpan(SourceLocation(sem.span.start.line, sem.span.start.column, sem.span.start.offset), SourceLocation(sem.span.start.line, sem.span.start.column + max(1, semantic_offset - sem.span.start.offset), semantic_offset + 1))
                diagnostic = SyntaxDiagnostic(phase="semantic", code=sem.code, message=sem.message, unexpected_token="LPAREN", unexpected_lexeme="(", span=span, diagnostic_id="OPT-SEM-0001", grammar_context="array_access")
                context = ErrorContext.from_diagnostic(diagnostic, baseline.tokens, source)
                semantic_prediction = predictor.predict_error_type(context)
            else:
                diagnostic = SyntaxDiagnostic(phase="semantic", code=sem.code, message=sem.message, unexpected_token="IDENTIFIER", unexpected_lexeme=getattr(sem, "identifier", None), span=sem.span, diagnostic_id="OPT-SEM-0001", grammar_context="declaration")
                context = ErrorContext.from_diagnostic(diagnostic, baseline.tokens, source)
                semantic_prediction = predictor.predict_error_type(context)
        if semantic_options:
            pred = semantic_prediction.to_dict() if semantic_prediction else {"label": "ARRAY_CALL_ERROR", "confidence": 0.93, "probabilities": {"ARRAY_CALL_ERROR": 0.93}}
            for item in semantic_options:
                item["confidence"] = semantic_prediction.confidence if semantic_prediction else item["confidence"]
                item["score"] = item["confidence"]
                item["predicted_class"] = semantic_prediction.label if semantic_prediction else "ARRAY_CALL_ERROR"
            review, ollama_meta = _ollama_review_and_fallback(source, context, semantic_prediction or predictor.predict_error_type(context), semantic_options[:limit], limit, use_ollama=use_ollama)
            return {
                "success": True,
                "original_code": source,
                "diagnostic": semantic.diagnostics[0].to_dict() if semantic and semantic.diagnostics else None,
                "prediction": pred,
                "options": review,
                "ollama": ollama_meta,
                "message": "Compiler-validated semantic alternatives reviewed by local Ollama when available.",
            }
        if declaration_alts:
            options = []
            pred_conf = semantic_prediction.confidence if semantic_prediction else 0.90
            pred_label = semantic_prediction.label if semantic_prediction else "DECLARATION_SEPARATOR_ERROR"
            for index, alternative in enumerate(declaration_alts[:limit], start=1):
                sem_count = _semantic_count(alternative)
                score = max(0.01, pred_conf - (index - 1) * 0.05)
                options.append({
                    "id": f"DECL-SEM-ALT-{index:02d}",
                    "label": f"Option {index}",
                    "corrected_code": alternative,
                    "score": score,
                    "confidence": score,
                    "predicted_class": pred_label,
                    "matched_class": "DECLARATION_SEPARATOR_ERROR",
                    "reason": "Compiler-valid declaration interpretation inferred from the semantic error",
                    "grammar_context": "declaration",
                    "candidate": None,
                    "validation": None,
                    "semantic_errors": sem_count,
                    "fully_valid": sem_count == 0,
                    "origin": "contextual_alternative",
                })
            pred_obj = semantic_prediction or predictor.predict_error_type(context)
            reviewed, ollama_meta = _ollama_review_and_fallback(source, context, pred_obj, options, limit, use_ollama=use_ollama)
            return {
                "success": True,
                "original_code": source,
                "diagnostic": None,
                "prediction": pred_obj.to_dict(),
                "options": reviewed,
                "ollama": ollama_meta,
                "message": "Compiler-valid declaration alternatives reviewed by local Ollama when available.",
            }
        return {
            "success": True,
            "original_code": source,
            "diagnostic": None,
            "prediction": None,
            "options": [],
            "message": "Source is syntactically valid; there are no syntax corrections to suggest.",
        }
    if baseline.lexical_errors and not baseline.syntax_errors:
        return {
            "success": False,
            "original_code": source,
            "diagnostic": None,
            "prediction": None,
            "options": [],
            "message": "The first error is lexical; edit the source or run Correct for lexical recovery.",
        }

    diagnostic = baseline.syntax_errors[0]
    context = ErrorContext.from_diagnostic(diagnostic, baseline.tokens, source)
    prediction = predictor.predict_error_type(context)
    candidates = list(generate_ml_candidates(source, diagnostic, context, prediction))
    candidates.extend(diagnostic.correction_candidates)
    candidates.extend(generate_compound_candidates(source, baseline.tokens, baseline.syntax_errors, diagnostic))
    candidates = _dedupe(candidates)

    ranked = rank_candidates(candidates, prediction, context=context)
    all_options: list[dict[str, Any]] = []
    seen_sources: set[str] = set()
    for ranked_item in ranked:
        candidate = replace(ranked_item.candidate, score=ranked_item.compatibility_score)
        validation = validate_candidate(source, candidate, target_diagnostic=diagnostic, baseline_result=baseline)
        if not validation.relevant_valid or validation.corrected_source == source:
            continue
        if validation.corrected_source in seen_sources:
            continue
        seen_sources.add(validation.corrected_source)
        semantic_errors = _semantic_count(validation.corrected_source)
        all_options.append({
            "id": candidate.id,
            "label": f"Option {len(all_options) + 1}",
            "corrected_code": validation.corrected_source,
            "score": ranked_item.compatibility_score,
            "confidence": prediction.probabilities.get(ranked_item.matched_class or "", ranked_item.compatibility_score),
            "predicted_class": prediction.label,
            "matched_class": ranked_item.matched_class,
            "reason": candidate.reason,
            "grammar_context": candidate.grammar_context,
            "candidate": candidate.to_dict(),
            "validation": validation.to_dict(),
            "safety": assess_repair(candidate, validation).to_dict(),
            "semantic_errors": semantic_errors if semantic_errors < 10_000 else None,
            "fully_valid": validation.valid and semantic_errors == 0,
            "origin": candidate.origin,
        })
        if len(all_options) >= limit:
            break

    # Prefer whole-program-valid alternatives when at least one exists. If none
    # exists, expose local-progress candidates so the user can still inspect
    # how the first error would be repaired.
    if any(item["fully_valid"] for item in all_options):
        options = [item for item in all_options if item["fully_valid"]]
    else:
        options = all_options

    # Add carefully constrained declaration alternatives that may be semantically
    # preferable to a purely local semicolon insertion.
    existing = {item["corrected_code"] for item in options}
    for alternative in _declaration_alternatives(source):
        if alternative in existing:
            continue
        sem_count = _semantic_count(alternative)
        options.append({
            "id": f"DECL-ALT-{len(options)+1:02d}",
            "label": f"Option {len(options)+1}",
            "corrected_code": alternative,
            "score": max(0.01, prediction.confidence * 0.92),
            "confidence": prediction.confidence,
            "predicted_class": prediction.label,
            "matched_class": "DECLARATION_ALTERNATIVE",
            "reason": "Alternative declaration structure suggested from the surrounding syntax",
            "grammar_context": "declaration",
            "candidate": None,
            "validation": None,
            "semantic_errors": sem_count,
            "fully_valid": sem_count == 0,
            "origin": "contextual_alternative",
        })
        existing.add(alternative)
        if len(options) >= limit:
            break

    if any(item["fully_valid"] for item in options):
        options = [item for item in options if item["fully_valid"]]
    contextual = _contextual_scenario_alternatives(source)
    existing_codes = {item["corrected_code"] for item in options}
    for item in contextual:
        if item["corrected_code"] not in existing_codes:
            options.append(item)
            existing_codes.add(item["corrected_code"])
    if not options:
        options = _local_pattern_alternatives(source)[:limit]
    # Never expose an invalid candidate alongside valid whole-program repairs.
    if any(item["fully_valid"] for item in options):
        options = [item for item in options if item["fully_valid"]]
    unique_options = {}
    for item in options:
        unique_options.setdefault(repair_key(item["corrected_code"]), item)
    options = list(unique_options.values())
    options.sort(key=lambda item: (not item["fully_valid"], -float(item["score"]), item["semantic_errors"] if item["semantic_errors"] is not None else 9999))
    options, ollama_meta = _ollama_review_and_fallback(source, context, prediction, options, limit, use_ollama=use_ollama)
    for index, item in enumerate(options, start=1):
        item["label"] = f"Option {index}"
    return {
        "success": True,
        "original_code": source,
        "diagnostic": diagnostic.to_dict(),
        "prediction": prediction.to_dict(),
        "options": options,
        "ollama": ollama_meta,
        "message": "Compiler-validated alternatives reviewed by local Ollama when available; ML is used for classification and ranking, with Ollama generation as fallback.",
    }
