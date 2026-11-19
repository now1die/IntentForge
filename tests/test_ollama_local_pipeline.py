import json
from ai.llm_fallback import OllamaFallbackService
from compiler.parser import parse
from ai.error_context import ErrorContext
from ai.error_predictor import ErrorPrediction

class FakeResponse:
    def __init__(self, payload): self.payload = json.dumps(payload).encode()
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return self.payload

class FakeOpener:
    def __init__(self): self.calls=[]
    def __call__(self, request, timeout=0):
        self.calls.append((request.full_url, request.method, json.loads(request.data.decode()) if request.data else None))
        if request.full_url.endswith('/api/tags'):
            return FakeResponse({'models':[{'name':'llama3.2:3b'}]})
        body = json.loads(request.data.decode())
        system = body['messages'][0]['content']
        if 'verifier' in system.lower():
            return FakeResponse({'message': {'content': json.dumps({'approved_ids':['A','B'],'scores':{'A':.9,'B':.8},'reason':'both plausible'})}})
        return FakeResponse({'message': {'content': json.dumps({'candidates':['int main(){ int x, y; return 0; }','int main(){ int x; int y; return 0; }'],'reason':'two declaration interpretations'})}})

def test_ollama_local_review_and_generation():
    opener=FakeOpener(); service=OllamaFallbackService(opener=opener)
    assert service.available
    source='int main(){int x y;}'
    parsed=parse(source); ctx=ErrorContext.from_diagnostic(parsed.syntax_errors[0], parsed.tokens, source)
    review=service.review_candidates(source, ctx, [{'id':'A','corrected_code':'a','reason':'r','fully_valid':True},{'id':'B','corrected_code':'b','reason':'r','fully_valid':True}])
    assert review.approved_ids == ('A','B')
    generated=service.generate_options(source, ctx, ErrorPrediction('DECLARATION_SEPARATOR_ERROR', .9, {'DECLARATION_SEPARATOR_ERROR': .9}))
    assert len(generated.candidates) == 2
    assert len(opener.calls) >= 3

def test_correction_options_uses_ollama_generation_when_ml_has_no_candidate(monkeypatch):
    from ai import correction_options as module
    from ai.error_predictor import MLCorrectionPredictor
    from ai.llm_fallback import LLMGeneratedOptionsResult, LLMReviewResult
    class FakeService:
        model='llama3.2:3b'; available=True
        def review_candidates(self, *args, **kwargs):
            return LLMReviewResult(True, True, self.model, approved_ids=tuple(c['id'] for c in args[2]), scores={c['id']:.9 for c in args[2]})
        def generate_options(self, *args, **kwargs):
            return LLMGeneratedOptionsResult(True, True, self.model, candidates=('int main(){ int x, y; return 0; }','int main(){ int x; int y; return 0; }'))
    monkeypatch.setattr(module, 'OllamaFallbackService', FakeService)
    result=module.suggest_correction_options('int main(){ int x y; return 0; }', MLCorrectionPredictor.load('models/syntax_error_classifier.joblib'))
    assert result['ollama']['mode'] in {'verification','generation_fallback'}
    assert result['options']
