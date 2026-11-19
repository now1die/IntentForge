# Local Ollama LLM fallback

The compiler can use a local Ollama model as a constrained fallback after compiler
candidate generation and ML classification. Ollama runs on the user's machine, so
no Groq/OpenAI/cloud API key is needed for this path.

## Local setup

1. Install Ollama on the PC.
2. Start the Ollama service.
3. Pull the configured model:

```powershell
ollama pull llama3.2:3b
```

4. Optional environment overrides:

```text
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:3b
OLLAMA_ENABLED=true
```

The backend checks `/api/tags` and only calls `/api/chat` when the configured model
is locally available. Use loopback or a trusted private network. An offline
service, missing model, or invalid configuration leaves the compiler and
bundled classifier available. The readiness check and inference request have
separate timeouts.

## Flow

1. Lexer/parser detect the error.
2. Traditional and ML candidate generation run first.
3. Compiler validation rejects invalid candidates.
4. If ambiguity remains or ML confidence is insufficient, the local Ollama model
   receives structured compiler context.
5. Ollama proposes one minimal structural edit or selects one of the supplied
   validated candidates.
6. The compiler validates the proposal again.
7. Ambiguous or behavior-changing candidates require explicit approval.

The direct correction path accepts bounded structural edits. The interactive
path can request whole-source alternatives when local candidates are empty.
It independently checks syntax and semantics and presents valid alternatives
for user review. Model review and compiler checks do not establish behavioral
equivalence.

## API

`GET /health` reports `ollama_configured` without exposing secrets. Correction
responses expose `ollama_fallback_used`. The frontend does not receive an API key.

## Verification

Run `python -m scripts.verify_ollama` from the repository root to discover the
configured model, request a real edit, and revalidate it. The command reports
discovery and inference timings in JSON. It exits with status 1 if the service
or model is unavailable, or the response cannot be validated. The Phase 1
environment did not have a reachable Ollama service. Mocked service tests
cover discovery, timeout, malformed JSON, empty replies and validation.
