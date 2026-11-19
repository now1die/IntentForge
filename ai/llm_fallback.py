"""Optional Groq fallback that proposes one structured Mini-C source edit."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from time import monotonic
from typing import Any, Protocol, Sequence

from dotenv import dotenv_values, find_dotenv, load_dotenv

from compiler.correction import CandidateValidation, CorrectionAction, CorrectionCandidate
from compiler.errors import SyntaxDiagnostic
from compiler.source_location import SourceLocation, SourceSpan

from .error_context import ErrorContext
from .error_predictor import ErrorPrediction


DEFAULT_GROQ_MODEL = "qwen/qwen3.8-27b"
DEFAULT_OLLAMA_MODEL = "llama3.2:3b"
DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_TIMEOUT = 12.0
MAX_OLLAMA_BODY = 256_000
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_TOKENS = 500
DEFAULT_SELECTION_MAX_TOKENS = 500
DEFAULT_AMBIGUITY_SELECTION_THRESHOLD = 0.75
MAX_REPLACEMENT_LENGTH = 80
SUPPORTED_ACTIONS = {
    CorrectionAction.INSERT.value,
    CorrectionAction.DELETE.value,
    CorrectionAction.REPLACE.value,
}
STRUCTURAL_TOKEN_TEXT = {
    "SEMICOLON": ";",
    "COMMA": ",",
    "LPAREN": "(",
    "RPAREN": ")",
    "LBRACKET": "[",
    "RBRACKET": "]",
    "LBRACE": "{",
    "RBRACE": "}",
}
KNOWN_KEYWORDS = {
    "int", "float", "char", "bool", "void", "if", "else", "while", "for",
    "break", "continue", "return",
}


@dataclass(frozen=True, slots=True)
class LLMSuggestion:
    action: CorrectionAction
    replacement_text: str
    target_start: int
    target_end: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "replacement_text": self.replacement_text,
            "target_start": self.target_start,
            "target_end": self.target_end,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class LLMFallbackResult:
    available: bool
    attempted: bool
    model: str
    suggestion: LLMSuggestion | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "attempted": self.attempted,
            "model": self.model,
            "suggestion": self.suggestion.to_dict() if self.suggestion else None,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class LLMCandidateSelection:
    selected_candidate_id: str | None
    confidence: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_candidate_id": self.selected_candidate_id,
            "confidence": self.confidence,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class LLMCandidateSelectionResult:
    available: bool
    attempted: bool
    model: str
    selection: LLMCandidateSelection | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "attempted": self.attempted,
            "model": self.model,
            "selection": self.selection.to_dict() if self.selection else None,
            "error": self.error,
        }

@dataclass(frozen=True, slots=True)
class LLMReviewResult:
    available: bool
    attempted: bool
    model: str
    approved_ids: tuple[str, ...] = ()
    scores: dict[str, float] | None = None
    reason: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available, "attempted": self.attempted, "model": self.model,
            "approved_ids": list(self.approved_ids), "scores": self.scores or {},
            "reason": self.reason, "error": self.error,
        }

@dataclass(frozen=True, slots=True)
class LLMGeneratedOptionsResult:
    available: bool
    attempted: bool
    model: str
    candidates: tuple[str, ...] = ()
    reason: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available, "attempted": self.attempted, "model": self.model,
            "candidates": list(self.candidates), "reason": self.reason, "error": self.error,
        }



class LLMFallbackService(Protocol):
    model: str

    def suggest(
        self, context: ErrorContext, prediction: ErrorPrediction
    ) -> LLMFallbackResult:
        """Return one structured edit suggestion without applying it."""
        ...

    def select_candidate(
        self,
        source: str,
        context: ErrorContext,
        candidates: Sequence[CandidateValidation],
    ) -> LLMCandidateSelectionResult:
        """Choose only an ID from compiler-generated, validated candidates."""
        ...

    def review_candidates(
        self, source: str, context: ErrorContext, candidates: Sequence[dict[str, Any]]
    ) -> LLMReviewResult:
        ...

    def generate_options(
        self, source: str, context: ErrorContext, prediction: ErrorPrediction
    ) -> LLMGeneratedOptionsResult:
        ...


class GroqFallbackService:
    """Small Groq adapter with dependency injection for offline testing."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = DEFAULT_GROQ_MODEL,
        client: Any | None = None,
        env_path: str | Path | None = None,
    ) -> None:
        self.model = model
        self._client = client
        self._api_key = api_key
        if client is None and api_key is None:
            dotenv_path = str(env_path) if env_path is not None else find_dotenv(usecwd=True)
            if dotenv_path:
                load_dotenv(dotenv_path=dotenv_path, override=False)
            self._api_key = os.getenv("GROQ_API_KEY")

    @property
    def available(self) -> bool:
        return self._client is not None or bool(self._api_key)

    def suggest(
        self, context: ErrorContext, prediction: ErrorPrediction
    ) -> LLMFallbackResult:
        if not self.available:
            return LLMFallbackResult(
                available=False,
                attempted=False,
                model=self.model,
                error="GROQ_API_KEY is unavailable",
            )
        try:
            client = self._client or self._create_client()
            completion = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": json.dumps(_structured_context(context, prediction)),
                    },
                ],
                temperature=DEFAULT_TEMPERATURE,
                max_tokens=DEFAULT_MAX_TOKENS,
                response_format={"type": "json_object"},
            )
            content = completion.choices[0].message.content
            suggestion = parse_llm_suggestion(content)
            return LLMFallbackResult(True, True, self.model, suggestion=suggestion)
        except (ValueError, TypeError, KeyError, IndexError, AttributeError, json.JSONDecodeError) as exc:
            return LLMFallbackResult(
                available=True,
                attempted=True,
                model=self.model,
                error=f"Malformed Groq response: {exc}",
            )
        except Exception as exc:  # SDK/network failures must not break the compiler.
            return LLMFallbackResult(
                available=True,
                attempted=True,
                model=self.model,
                error=f"Groq request failed: {type(exc).__name__}",
            )

    def select_candidate(
        self,
        source: str,
        context: ErrorContext,
        candidates: Sequence[CandidateValidation],
    ) -> LLMCandidateSelectionResult:
        """Ask Groq to select an existing validated candidate, never an edit."""

        if not self.available:
            return LLMCandidateSelectionResult(
                available=False,
                attempted=False,
                model=self.model,
                error="GROQ_API_KEY is unavailable",
            )
        candidate_ids = {
            validation.candidate.id
            for validation in candidates
            if validation.relevant_valid
        }
        if len(candidate_ids) < 2:
            return LLMCandidateSelectionResult(
                available=True,
                attempted=False,
                model=self.model,
                error="Ambiguity selection requires at least two validated candidates",
            )
        try:
            client = self._client or self._create_client()
            completion = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": _SELECTION_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": json.dumps(
                            _selection_context(source, context, candidates)
                        ),
                    },
                ],
                temperature=DEFAULT_TEMPERATURE,
                max_tokens=DEFAULT_SELECTION_MAX_TOKENS,
                reasoning_effort="none",
                response_format=_candidate_selection_response_format(candidate_ids),
            )
            content = completion.choices[0].message.content
            selection = parse_candidate_selection(content, candidate_ids)
            return LLMCandidateSelectionResult(
                True, True, self.model, selection=selection
            )
        except (ValueError, TypeError, KeyError, IndexError, AttributeError, json.JSONDecodeError) as exc:
            return LLMCandidateSelectionResult(
                available=True,
                attempted=True,
                model=self.model,
                error=f"Malformed Groq selection response: {exc}",
            )
        except Exception as exc:  # SDK/network failures must not break the compiler.
            return LLMCandidateSelectionResult(
                available=True,
                attempted=True,
                model=self.model,
                error=f"Groq selection request failed: {type(exc).__name__}",
            )

    def _create_client(self) -> Any:
        from groq import Groq

        self._client = Groq(api_key=self._api_key)
        return self._client



class RejectOllamaRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class OllamaFallbackService:
    """Local Ollama adapter. No cloud API key is required."""

    def __init__(
        self,
        *,
        host: str | None = None,
        model: str | None = None,
        timeout: float = DEFAULT_OLLAMA_TIMEOUT,
        opener: Any | None = None,
    ) -> None:
        settings = dotenv_values(Path(__file__).resolve().parents[1] / ".env")
        self.host = (host or os.getenv("OLLAMA_HOST") or settings.get("OLLAMA_HOST") or DEFAULT_OLLAMA_HOST).rstrip("/")
        self.model = (model or os.getenv("OLLAMA_MODEL") or settings.get("OLLAMA_MODEL") or DEFAULT_OLLAMA_MODEL).strip()
        enabled = (os.getenv("OLLAMA_ENABLED") or settings.get("OLLAMA_ENABLED") or "true").lower()
        self.timeout = timeout
        self._opener = opener
        self.configuration_error = None
        try:
            endpoint = urlsplit(self.host)
            if (
                endpoint.scheme not in {"http", "https"} or not endpoint.hostname
                or endpoint.username is not None or endpoint.password is not None
                or endpoint.path or endpoint.query or endpoint.fragment
                or (endpoint.port is not None and endpoint.port == 0)
            ):
                raise ValueError("OLLAMA_HOST must be an HTTP(S) origin without credentials, a path, or a query")
            if not self.model or any(c.isspace() for c in self.model):
                raise ValueError("OLLAMA_MODEL must be a nonempty model name")
            if enabled not in {"true", "false"}:
                raise ValueError("OLLAMA_ENABLED must be true or false")
            if not math.isfinite(timeout) or not 0 < timeout <= 30:
                raise ValueError("Ollama timeout must be in (0, 30] seconds")
        except ValueError as exc:
            self.configuration_error = str(exc)
        self.enabled = enabled == "true"

    @property
    def unavailable_reason(self) -> str:
        if self.configuration_error:
            return self.configuration_error
        if not self.enabled:
            return "Ollama is disabled by OLLAMA_ENABLED"
        return f"Ollama is unavailable at {self.host} or model {self.model!r} is not installed"

    @property
    def available(self) -> bool:
        if self.configuration_error or not self.enabled:
            return False
        try:
            payload = self._request("/api/tags", method="GET", body=None, timeout=min(self.timeout, 1.5))
            models = payload.get("models", []) if isinstance(payload, dict) else []
            names = {item.get("name", item.get("model")) for item in models if isinstance(item, dict)}
            requested = self.model if ":" in self.model.rsplit("/", 1)[-1] else self.model + ":latest"
            return self.model in names or requested in names
        except Exception:
            return False

    def suggest(
        self, context: ErrorContext, prediction: ErrorPrediction
    ) -> LLMFallbackResult:
        if not self.available:
            return LLMFallbackResult(
                available=False,
                attempted=False,
                model=self.model,
                error=self.unavailable_reason,
            )
        try:
            payload = self._chat(_SYSTEM_PROMPT, _structured_context(context, prediction))
            content = _extract_ollama_content(payload)
            suggestion = parse_llm_suggestion(content)
            return LLMFallbackResult(True, True, self.model, suggestion=suggestion)
        except (ValueError, TypeError, KeyError, IndexError, json.JSONDecodeError) as exc:
            return LLMFallbackResult(True, True, self.model, error=f"Malformed Ollama response: {exc}")
        except Exception as exc:
            return LLMFallbackResult(True, True, self.model, error=f"Ollama request failed: {type(exc).__name__}")

    def select_candidate(
        self,
        source: str,
        context: ErrorContext,
        candidates: Sequence[CandidateValidation],
    ) -> LLMCandidateSelectionResult:
        candidate_ids = {
            validation.candidate.id
            for validation in candidates
            if validation.relevant_valid
        }
        if len(candidate_ids) < 2:
            return LLMCandidateSelectionResult(
                available=self.available,
                attempted=False,
                model=self.model,
                error="Ambiguity selection requires at least two validated candidates",
            )
        if not self.available:
            return LLMCandidateSelectionResult(
                available=False,
                attempted=False,
                model=self.model,
                error=self.unavailable_reason,
            )
        try:
            payload = self._chat(_SELECTION_SYSTEM_PROMPT, _selection_context(source, context, candidates))
            content = _extract_ollama_content(payload)
            selection = parse_candidate_selection(content, candidate_ids)
            return LLMCandidateSelectionResult(True, True, self.model, selection=selection)
        except (ValueError, TypeError, KeyError, IndexError, json.JSONDecodeError) as exc:
            return LLMCandidateSelectionResult(True, True, self.model, error=f"Malformed Ollama selection response: {exc}")
        except Exception as exc:
            return LLMCandidateSelectionResult(True, True, self.model, error=f"Ollama selection request failed: {type(exc).__name__}")

    def review_candidates(
        self, source: str, context: ErrorContext, candidates: Sequence[dict[str, Any]]
    ) -> LLMReviewResult:
        if not self.available:
            return LLMReviewResult(False, False, self.model, error=self.unavailable_reason)
        if not candidates:
            return LLMReviewResult(True, False, self.model, reason="No candidates to review")
        try:
            payload = self._chat(_REVIEW_SYSTEM_PROMPT, {
                "original_source": source,
                "diagnostic": _context_for_llm(context),
                "candidates": candidates,
            })
            content = _extract_ollama_content(payload)
            data = json.loads(content)
            allowed_ids = {item["id"] for item in candidates}
            approved_ids = data.get("approved_ids", [])
            if not isinstance(approved_ids, list) or any(not isinstance(item, str) for item in approved_ids):
                raise ValueError("approved_ids must be a list of candidate IDs")
            approved = tuple(dict.fromkeys(item for item in approved_ids if item in allowed_ids))
            scores_raw = data.get("scores", {})
            if not isinstance(scores_raw, dict):
                raise ValueError("scores must be an object")
            scores = {
                key: max(0.0, min(1.0, value))
                for key, value in scores_raw.items()
                if key in allowed_ids and type(value) in (int, float) and math.isfinite(value)
            }
            return LLMReviewResult(True, True, self.model, approved_ids=approved, scores=scores, reason=str(data.get("reason", ""))[:500])
        except Exception as exc:
            return LLMReviewResult(True, True, self.model, error=f"Ollama review failed: {type(exc).__name__}")

    def generate_options(
        self, source: str, context: ErrorContext, prediction: ErrorPrediction
    ) -> LLMGeneratedOptionsResult:
        if not self.available:
            return LLMGeneratedOptionsResult(False, False, self.model, error=self.unavailable_reason)
        try:
            payload = self._chat(_GENERATION_SYSTEM_PROMPT, {
                "original_source": source,
                "diagnostic": _context_for_llm(context),
                "ml_prediction": prediction.to_dict(),
            })
            content = _extract_ollama_content(payload)
            data = json.loads(content)
            candidates = data.get("candidates", [])
            if not isinstance(candidates, list):
                raise ValueError("candidates must be a list")
            clean = tuple(item for item in candidates if isinstance(item, str) and item.strip() and len(item) <= 100_000)[:8]
            return LLMGeneratedOptionsResult(True, True, self.model, candidates=clean, reason=str(data.get("reason", ""))[:500])
        except Exception as exc:
            return LLMGeneratedOptionsResult(True, True, self.model, error=f"Ollama generation failed: {type(exc).__name__}")

    def _chat(self, system_prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        return self._request(
            "/api/chat",
            method="POST",
            body={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(context)},
                ],
                "stream": False,
                "format": "json",
                "options": {"temperature": DEFAULT_TEMPERATURE, "num_predict": 1024},
            },
            timeout=self.timeout,
        )

    def _request(
        self,
        path: str,
        *,
        method: str,
        body: dict[str, Any] | None,
        timeout: float,
    ) -> dict[str, Any]:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(
            f"{self.host}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"} if body is not None else {},
        )
        opener = self._opener or build_opener(RejectOllamaRedirect()).open
        deadline = monotonic() + timeout
        raw = bytearray()
        with opener(request, timeout=timeout) as response:
            read = getattr(response, "read1", response.read)
            while monotonic() < deadline:
                chunk = read(min(8192, MAX_OLLAMA_BODY + 1 - len(raw)))
                if not chunk:
                    break
                raw.extend(chunk)
                if len(raw) > MAX_OLLAMA_BODY:
                    raise ValueError("Ollama response exceeds its byte limit")
            if monotonic() >= deadline:
                raise TimeoutError("Ollama response exceeded the request budget")
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Ollama response must be a JSON object")
        return payload


def _extract_ollama_content(payload: dict[str, Any]) -> str:
    message = payload.get("message")
    if isinstance(message, dict) and isinstance(message.get("content"), str):
        return message["content"]
    # Older/local-compatible endpoints sometimes return a direct response field.
    if isinstance(payload.get("response"), str):
        return payload["response"]
    raise ValueError("Ollama response did not contain message.content")

def parse_llm_suggestion(content: str | None) -> LLMSuggestion:
    if not isinstance(content, str) or not content.strip():
        raise ValueError("response content is empty")
    payload = json.loads(content)
    required = {"action", "replacement_text", "target_start", "target_end", "reason"}
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("response must contain exactly the required edit fields")
    action_text = payload["action"]
    replacement = payload["replacement_text"]
    start = payload["target_start"]
    end = payload["target_end"]
    reason = payload["reason"]
    if action_text not in SUPPORTED_ACTIONS:
        raise ValueError("unsupported action")
    if not isinstance(replacement, str) or len(replacement) > MAX_REPLACEMENT_LENGTH:
        raise ValueError("replacement_text is invalid")
    if type(start) is not int or type(end) is not int or start < 0 or end < start:
        raise ValueError("target range is invalid")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("reason is required")
    action = CorrectionAction(action_text)
    if action is CorrectionAction.INSERT and start != end:
        raise ValueError("INSERT requires a zero-width target")
    if action is CorrectionAction.DELETE and replacement != "":
        raise ValueError("DELETE requires empty replacement_text")
    if action in {CorrectionAction.DELETE, CorrectionAction.REPLACE} and start == end:
        raise ValueError(f"{action.value} requires a non-empty target")
    return LLMSuggestion(action, replacement, start, end, reason.strip())


def parse_candidate_selection(
    content: str | None,
    allowed_candidate_ids: set[str] | None = None,
) -> LLMCandidateSelection:
    if not isinstance(content, str) or not content.strip():
        raise ValueError("response content is empty")
    payload = json.loads(content)
    required = {"selected_candidate_id", "confidence", "reason"}
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("response must contain exactly the required selection fields")
    candidate_id = payload["selected_candidate_id"]
    confidence = payload["confidence"]
    reason = payload["reason"]
    if candidate_id is not None and not isinstance(candidate_id, str):
        raise ValueError("selected_candidate_id must be a string or null")
    if (
        candidate_id is not None
        and allowed_candidate_ids is not None
        and candidate_id not in allowed_candidate_ids
    ):
        raise ValueError("selected_candidate_id is not one of the supplied candidates")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ValueError("confidence must be a number")
    if not 0.0 <= float(confidence) <= 1.0:
        raise ValueError("confidence must be between 0 and 1")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("reason is required")
    return LLMCandidateSelection(candidate_id, float(confidence), reason.strip())


def free_form_suggestion_rejection(
    suggestion: LLMSuggestion,
    context: ErrorContext,
    source: str,
) -> str | None:
    """Reject free-form edits that are not structural and compiler-evidenced."""

    start = suggestion.target_start
    end = suggestion.target_end
    if not (0 <= start <= end <= len(source)):
        return "target_range_outside_source"

    if suggestion.action is CorrectionAction.INSERT:
        token_type = next(
            (
                name
                for name, text in STRUCTURAL_TOKEN_TEXT.items()
                if text == suggestion.replacement_text
            ),
            None,
        )
        if token_type is None:
            return "semantic_content_invention_is_forbidden"
        if token_type not in context.expected_tokens:
            return "inserted_structure_is_not_expected_by_the_parser"
        if not _is_local_whitespace_insertion(start, context, source):
            return "structural_insertion_is_outside_the_diagnostic_boundary"
        return None

    matching = next(
        (
            candidate
            for candidate in context.correction_candidates
            if candidate.action is suggestion.action
            and candidate.span.start.offset == start
            and candidate.span.end.offset == end
            and candidate.text == suggestion.replacement_text
        ),
        None,
    )
    if matching is None:
        return "edit_is_not_supported_by_a_compiler_generated_candidate"

    original = source[start:end]
    if suggestion.action is CorrectionAction.DELETE:
        if not original or any(character.isalnum() or character == "_" for character in original):
            return "deleting_identifiers_literals_or_keywords_is_forbidden"
        return None

    replacement = suggestion.replacement_text
    structural_replacement = (
        original in STRUCTURAL_TOKEN_TEXT.values()
        and replacement in STRUCTURAL_TOKEN_TEXT.values()
    ) or (
        original
        and replacement
        and not any(character.isalnum() or character == "_" for character in original)
        and not any(character.isalnum() or character == "_" for character in replacement)
    )
    keyword_replacement = (
        replacement in KNOWN_KEYWORDS
        and original.isidentifier()
        and matching.token_type is not None
    )
    if structural_replacement or keyword_replacement:
        return None
    return "semantic_content_invention_is_forbidden"


def _is_local_whitespace_insertion(
    offset: int,
    context: ErrorContext,
    source: str,
) -> bool:
    current_offset = (
        context.current_token.offset if context.current_token is not None else len(source)
    )
    previous_end = (
        context.previous_tokens[-1].offset + len(context.previous_tokens[-1].lexeme)
        if context.previous_tokens
        else current_offset
    )
    if not previous_end <= offset <= current_offset:
        return False
    return not source[previous_end:current_offset].strip()


def _candidate_selection_response_format(candidate_ids: set[str]) -> dict[str, Any]:
    """Constrain Groq output to the supplied IDs or an explicit unresolved result."""

    return {
        "type": "json_schema",
        "json_schema": {
            "name": "compiler_candidate_selection",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "selected_candidate_id": {
                        "enum": [*sorted(candidate_ids), None],
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                    "reason": {
                        "type": "string",
                        "maxLength": 240,
                    },
                },
                "required": ["selected_candidate_id", "confidence", "reason"],
                "additionalProperties": False,
            },
        },
    }


def suggestion_to_candidate(
    suggestion: LLMSuggestion,
    diagnostic: SyntaxDiagnostic,
    source: str,
) -> CorrectionCandidate:
    """Convert the LLM schema to the compiler's existing edit representation."""

    if suggestion.target_end > len(source):
        raise ValueError("LLM target range is outside the source text")
    start = _location(source, suggestion.target_start)
    end = _location(source, suggestion.target_end)
    original = source[suggestion.target_start : suggestion.target_end]
    return CorrectionCandidate(
        id=f"{diagnostic.diagnostic_id}-llm",
        action=suggestion.action,
        token_type=None,
        token_lexeme=original or None,
        offset=suggestion.target_start,
        span=SourceSpan(start, end),
        text=suggestion.replacement_text,
        reason=suggestion.reason,
        grammar_context=diagnostic.grammar_context or "unknown",
        diagnostic_id=diagnostic.diagnostic_id,
        origin="llm_fallback",
    )


def _location(source: str, offset: int) -> SourceLocation:
    prefix = source[:offset]
    line = prefix.count("\n") + 1
    newline = prefix.rfind("\n")
    column = offset + 1 if newline < 0 else offset - newline
    return SourceLocation(line, column, offset)


def _structured_context(
    context: ErrorContext, prediction: ErrorPrediction
) -> dict[str, Any]:
    return {
        "language": "Mini-C",
        "instruction": (
            "Propose exactly one minimal compiler-evidenced structural syntax edit using "
            "absolute source offsets. Never invent identifiers, operands, literals, calls, "
            "expressions, conditions, declarations, or semantic values."
        ),
        "grammar_context": context.grammar_context,
        "unexpected_token": context.unexpected_token,
        "unexpected_lexeme": context.unexpected_lexeme,
        "expected_tokens": list(context.expected_tokens),
        "previous_tokens": [item.to_dict() for item in context.previous_tokens],
        "current_token": context.current_token.to_dict() if context.current_token else None,
        "next_tokens": [item.to_dict() for item in context.next_tokens],
        "nearby_source": context.nearby_source,
        "snippet_start_offset": context.metadata.get("snippet_start_offset"),
        "snippet_end_offset": context.metadata.get("snippet_end_offset"),
        "delimiter_depth": dict(context.delimiter_depth),
        "traditional_candidates": [item.to_dict() for item in context.correction_candidates],
        "ml_prediction": prediction.to_dict(),
        "required_output": {
            "action": "INSERT | DELETE | REPLACE",
            "replacement_text": "string",
            "target_start": "integer",
            "target_end": "integer",
            "reason": "short string",
        },
    }


def _selection_context(
    source: str,
    context: ErrorContext,
    candidates: Sequence[CandidateValidation],
) -> dict[str, Any]:
    return {
        "language": "Mini-C",
        "task": "Select the most plausible programmer-intent repair from the supplied validated candidates.",
        "original_source": source,
        "diagnostic": {
            "grammar_context": context.grammar_context,
            "unexpected_token": context.unexpected_token,
            "unexpected_lexeme": context.unexpected_lexeme,
            "expected_tokens": list(context.expected_tokens),
            "previous_tokens": [item.to_dict() for item in context.previous_tokens],
            "current_token": context.current_token.to_dict() if context.current_token else None,
            "next_tokens": [item.to_dict() for item in context.next_tokens],
            "delimiter_depth": dict(context.delimiter_depth),
        },
        "validated_candidates": [
            {
                "candidate_id": validation.candidate.id,
                "action": validation.candidate.action.value,
                "token_type": validation.candidate.token_type,
                "token_lexeme": validation.candidate.token_lexeme,
                "target_start": validation.candidate.span.start.offset,
                "target_end": validation.candidate.span.end.offset,
                "replacement_text": validation.candidate.text,
                "compiler_reason": validation.candidate.reason,
                "edits": [
                    edit.to_dict() for edit in validation.candidate.edits
                ],
                "corrected_source": validation.corrected_source,
                "parser_validation": {
                    "valid": validation.valid,
                    "relevant_valid": validation.relevant_valid,
                    "remaining_lexical_errors": validation.remaining_lexical_errors,
                    "remaining_syntax_errors": validation.remaining_syntax_errors,
                },
            }
            for validation in candidates
            if validation.relevant_valid
        ],
        "selection_policy": (
            "Choose exactly one supplied candidate ID only when it is clearly more plausible. "
            "Otherwise return null. Never propose source text or a new edit."
        ),
        "required_output": {
            "selected_candidate_id": "supplied candidate_id string | null",
            "confidence": "number from 0 to 1",
            "reason": "short explanation",
        },
    }


def _context_for_llm(context: ErrorContext) -> dict[str, Any]:
    return {
        "phase": context.phase, "message": context.message,
        "grammar_context": context.grammar_context,
        "unexpected_token": context.unexpected_token,
        "unexpected_lexeme": context.unexpected_lexeme,
        "expected_tokens": list(context.expected_tokens),
        "previous_tokens": [item.to_dict() for item in context.previous_tokens],
        "current_token": context.current_token.to_dict() if context.current_token else None,
        "next_tokens": [item.to_dict() for item in context.next_tokens],
        "nearby_source": context.nearby_source,
    }


_REVIEW_SYSTEM_PROMPT = """You are the local Ollama verifier for a Mini-C compiler.
The compiler has already generated and validated the candidate corrections below.
Review programmer intent and reject candidates that invent unsupported semantics,
change unrelated code, or contradict the diagnostic. You may approve multiple
candidates because the UI is intentionally user-selectable. Never invent a new
candidate here. Return ONLY JSON: {\"approved_ids\":[candidate ids],\"scores\":{candidate_id:0..1},\"reason\":\"short reason\"}.
If intent is ambiguous, approve the candidates that are technically plausible and
keep their scores close rather than pretending one is certain."""

_GENERATION_SYSTEM_PROMPT = """You are the local Ollama fallback for a Mini-C compiler.
The ML classifier could not produce a suitable repair. Generate up to 5 complete
possible corrected Mini-C programs for the supplied source and diagnostic. Preserve
all original identifiers, literals, statements and intent unless the diagnostic
requires a structural repair. Do not invent unrelated program logic. It is okay to
return multiple alternatives when the programmer's intent is ambiguous. Return ONLY
JSON: {\"candidates\":[\"complete corrected source\", ...],\"reason\":\"short reason\"}."""


_SYSTEM_PROMPT = """You are a constrained Mini-C syntax correction fallback.
Use only the supplied compiler context. Propose one minimal syntax edit, not a
rewritten program. Return one JSON object with exactly these fields: action,
replacement_text, target_start, target_end, reason. action must be INSERT, DELETE,
or REPLACE. Offsets are absolute and the target range is half-open. For INSERT,
target_start must equal target_end. For DELETE, replacement_text must be empty.
Only propose compiler-evidenced punctuation, delimiter, operator, or known-keyword
repairs. Never invent identifiers, operands, literals, function calls, expressions,
declarations, return values, conditions, or other semantic program content.
Do not include Markdown, explanations outside JSON, or additional fields."""


_SELECTION_SYSTEM_PROMPT = """You are a constrained Mini-C correction candidate selector.
You may choose only one candidate_id from the validated_candidates supplied by the
compiler, or null when programmer intent is uncertain. Never propose, rewrite, or
describe a new edit. Return exactly one JSON object with selected_candidate_id,
confidence, and reason. Do not include Markdown or text outside the JSON object."""
