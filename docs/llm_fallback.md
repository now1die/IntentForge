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
```

The backend checks `/api/tags` and only calls `/api/chat` when the configured model
is locally available. If Ollama is offline or the model is missing, the compiler
continues without the fallback and never blocks normal ML/compiler correction.

## Flow

1. Lexer/parser detect the error.
2. Traditional and ML candidate generation run first.
3. Compiler validation rejects invalid candidates.
4. If ambiguity remains or ML confidence is insufficient, the local Ollama model
   receives structured compiler context.
5. Ollama proposes one minimal structural edit or selects one of the supplied
   validated candidates.
6. The compiler validates the proposal again.
7. Only a compiler-valid repair can be applied.

Ollama never has authority to rewrite the whole program or invent identifiers,
operands, literals, or semantic content.

## API

`GET /health` reports `ollama_configured` without exposing secrets. Correction
responses expose `ollama_fallback_used`. The frontend does not receive an API key.
