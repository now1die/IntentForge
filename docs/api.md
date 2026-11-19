# FastAPI backend (Phase 8)

The backend is a thin transport adapter around the existing compiler, semantic
analyzer, ML predictor, correction orchestrator, and local Ollama fallback:

```text
Future React + Monaco frontend
              ↓
          FastAPI routes
              ↓
Existing compiler / ML / local Ollama pipeline
```

No lexer, grammar, recovery, ranking, or source-correction rules live in the
routes. The API calls the existing domain functions and their `to_dict()`
serializers.

## Run locally

Install dependencies and start Uvicorn from the repository root:

```powershell
py -m pip install -r requirements.txt
py -m uvicorn backend.app.main:app --reload
```

The API defaults to `http://127.0.0.1:8000`. Interactive Swagger documentation
is available at `http://127.0.0.1:8000/docs`, and the OpenAPI document is at
`http://127.0.0.1:8000/openapi.json`.

## Request body

All POST endpoints accept the same Pydantic model:

```json
{
  "code": "int main() { return 0; }"
}
```

`code` is required, must be a string, and is limited to 100,000 characters.
Unknown request fields are rejected.

## Endpoints

### `GET /health`

Returns safe component readiness:

```json
{
  "status": "ok",
  "ml_model_loaded": true,
  "ollama_configured": true
}
```

The response reports only booleans and never includes environment values or
secrets.

### `POST /analyze`

Runs lexical, syntax, and—only after valid syntax—semantic analysis. It returns
token count, structured diagnostic sections, the existing AST JSON, and the
existing scoped symbol-table JSON.

```json
{
  "success": false,
  "token_count": 8,
  "lexical": {"success": true, "errors": []},
  "syntax": {"success": false, "errors": [{"code": "UNEXPECTED_EOF"}]},
  "semantic": {"ran": false, "success": null, "errors": []},
  "ast": null,
  "symbols": null
}
```

This endpoint never performs automatic correction.

### `POST /tokens`

Returns the deterministic lexer token stream and lexical diagnostics. Each token
contains type, lexeme, parsed value, line, column, offset, and its half-open source
span.

### `POST /ast`

Returns the existing AST serialization when parsing succeeds. Lexical or syntax
failure returns `ast: null` with structured diagnostics.

### `POST /symbols`

Runs the existing semantic pipeline. When syntax is valid, it returns the scoped
symbol table and semantic diagnostics. Otherwise `ran` is false and compiler
diagnostics explain why.

### `POST /correct`

Invokes the existing Phase 6/7 orchestrator. The response includes:

- original and corrected code
- correction and syntax-validity status
- number of applied corrections
- ordered correction history
- ML predictions and confidence values
- whether Ollama was actually called
- future-fallback status
- unresolved syntax diagnostics
- separate post-correction semantic diagnostics
- stop reason

A review-required edit uses `status: SUGGESTED`, preserves the current source
as `corrected_code`, and includes the proposal at
`history[].validation.corrected_source`. An ambiguous unresolved result keeps
candidate validation records in `history[].attempts`. History and interactive
options can contain additive `safety` metadata with category, reason and
whether explicit review is required. A successful AI candidate selection
means that the candidate passed validation. Use `applied` and
`corrections_applied` to determine what the orchestrator applied.

The cached predictor avoids loading the Joblib artifact on every request. A missing or
unreadable model returns HTTP `503` without preventing the server or analysis
endpoints from starting.

## HTTP error policy

Compiler errors in submitted Mini-C are normal results and return HTTP `200` with
diagnostics. Missing fields, malformed JSON, wrong types, extra fields, and overly
large source bodies return FastAPI/Pydantic validation responses (normally HTTP
`422`). Unexpected backend failures return a generic HTTP `500` message without a
Python traceback.

Ollama failures are represented in the fallback record.

## CORS

Development CORS permits only:

- `http://localhost:5173`
- `http://127.0.0.1:5173`

Allowed methods are `GET`, `POST`, and `OPTIONS`. Add exact HTTP(S) origins
using the API process variable `CORS_ALLOWED_ORIGINS` for a split deployment.
