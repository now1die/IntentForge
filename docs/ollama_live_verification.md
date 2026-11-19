# Ollama live verification

`LIVE_OLLAMA_STATUS=NOT_VERIFIED`

The configured model was `llama3.2:3b` at `http://127.0.0.1:11434`. A
direct request to `/api/tags` returned connection refused. The benchmark
probe reported unavailable after about 12 ms of local discovery. No
inference ran, no model response was received, and no live-results file
was generated. Compilation and offline ML verification completed.

Mocked tests exercise exact model tags, unavailable service, timeout,
malformed and empty payloads, constrained candidate selection, edit
parsing, and compiler revalidation. Safety checks are applied even when
a candidate has been validated and the provider recommends it. Only
bounded source edits are considered by the direct fallback. Ambiguous or
behavior-changing proposals still require approval.

To reproduce live checks on a machine that already has the model, leave
Ollama on loopback or a trusted private network. Run from the repository root:

```sh
ollama list
python -m scripts.verify_ollama
python -m scripts.verify_ollama --benchmark --out benchmarks/reports/ollama-live-results.json
```

The benchmark probe forces the established structured fallback on five
frozen cases covering a semicolon, a control closer, an array closer,
an ambiguous loop return, and a comparison operator. It records discovery
latency, inference and validation time, received and rejected responses,
compiler validation, reference adjudication, and review status. It writes
the live file only after receiving a model response. A timeout before a
response does not create a results file. The optional hosted workflow
job is manual and applies only on the repository's default branch with a
trusted runner labeled `intentforge-ollama`. Regular CI uses mocks.
