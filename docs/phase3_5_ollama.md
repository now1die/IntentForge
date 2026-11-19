# Optional Ollama

**LIVE_OLLAMA_STATUS=NOT_VERIFIED**

The configured model tag was `llama3.2:3b`. The local probe found no
reachable service or installed configured model. No live response,
latency comparison, or model version was verified. The observed
discovery report is stored separately from mocked results.
[Discovery observation](../benchmarks/reports/phase35-ollama-status.json)

The adapter now reads responses incrementally with a 256 KB cap,
blocks redirects, limits generated tokens and checks the request deadline
during reading. Socket calls use a transport timeout. The
structured-response parser and correction validator still gate model
suggestions. The correction orchestrator requires explicit approval
for both generated and selected Ollama advice, including preview. Tests use stubs for malformed, oversized and missing
responses. The compiler and intention analysis can run offline.

With an operator-provisioned service and model, reproduce with:

```bash
ollama list
ollama --version
OLLAMA_ENABLED=true OLLAMA_HOST=http://127.0.0.1:11434 OLLAMA_MODEL=llama3.2:3b \
  python -m scripts.verify_ollama --benchmark --out /tmp/phase35-ollama-live.json
python -m benchmarks.run --no-ollama --check
```

An unavailable service exits nonzero and prints its discovery result.
The live results file is created only after receiving a model response.
