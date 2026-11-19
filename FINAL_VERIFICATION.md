# AI Compiler — Final ML + Local Ollama Verification

## Final architecture
- **25-class local ML classifier** (scikit-learn / joblib).
- **3,200 records** used for training: 2,400 existing records + 800 adversarial scenario records.
- 80/20 stratified split, seed 42: **2,560 train / 640 held-out**, controlled held-out accuracy **100%**.
- New learned classes: `DECLARATION_DOT_ERROR`, `DECLARATION_COLON_ERROR`, `SCALAR_ARRAY_USE_ERROR`, `ARRAY_BRACE_INDEX_ERROR`.
- Local Ollama is the active LLM path: `http://127.0.0.1:11434`, default model `llama3.2:3b`.
- No cloud API key is required for the active correction path.
- Compiler parsing/semantic validation remains the final authority.
- Compiler-valid ML candidates are reviewed by local Ollama before they are exposed by the interactive correction-options pipeline when Ollama is available.
- If ML/compiler candidate generation produces no suitable options, local Ollama can generate up to 5 complete candidate programs. Every generated program is independently parsed and semantically checked before it can be displayed.
- Invalid candidates are never shown when valid whole-program alternatives exist.
- UI supports multiple alternatives, user selection, custom correction, and editing the original source.
- Fixed the selected-preview editor crash by making diagnostics optional-safe.

## Critical adversarial cases
1. `int main(){ int arr; arr{5]=10; return 0; }`
   - ML: `SCALAR_ARRAY_USE_ERROR` (~98.5% in the final model).
   - Valid option: `int arr[6]; arr[5]=10; ...`.
2. `int main(){ int arr[6]; arr{5]=10; return 0; }`
   - ML: `ARRAY_BRACE_INDEX_ERROR` (~98.5%).
   - Valid option: `arr[5]=10`.
3. `int main(){ int a.b; return 0; }`
   - ML: `DECLARATION_DOT_ERROR` (~97.2%).
   - Two valid alternatives: `int a, b;` and separate declarations.
4. `int main(){ int x;y; return 0; }`
   - ML: `DECLARATION_SEPARATOR_ERROR` (~97.3%).
   - Two valid alternatives: combined declaration and separate declarations.

## Verification runs
- Full repository pytest: **448 passed**, then repeated successfully (**448 passed**).
- General compiler suite: **220/220 PASS**, repeated successfully.
- Keyboard/array regression: **65/65 exact**, 0 failed, 0 crashes, repeated successfully.
- Stress suite: **3,758 cases executed twice**, with no Python exceptions. The existing stress harness intentionally labels exploratory cases as `PASS`, `REVIEW_ACCEPTED`, `REVIEW_REJECTED`, or `OBSERVED`; this is not a claim that all 3,758 are expected repairs.
- Adversarial ML scenario matrix: **400/400 exact class predictions** for the generated 4-class scenario set used in the direct prediction check.
- Local Ollama adapter tests: model discovery, candidate verification, and candidate-generation fallback all pass against a mocked local Ollama HTTP endpoint.

## Packaging note
A live Ollama daemon was not available inside the build environment, so live inference itself was not run here. The local Ollama HTTP adapter was exercised with a mock server, and the final project is configured to call the real local endpoint on the user's PC. Frontend dependency installation could not complete within the build environment's network timeout; the frontend source is included and should be installed with `npm.cmd install` on Windows.
