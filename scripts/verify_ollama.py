"""Check that the local Ollama service and configured model are reachable."""
from ai.llm_fallback import OllamaFallbackService

service = OllamaFallbackService()
print(f"Ollama host : {service.host}")
print(f"Ollama model: {service.model}")
print(f"Available   : {'YES' if service.available else 'NO'}")
if not service.available:
    print("Install/start Ollama and run: ollama pull " + service.model)
    raise SystemExit(1)
