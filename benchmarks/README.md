# Phase 1 correction benchmark

Run from the repository root using the shipped model and the pinned Python
environment.

```sh
python -m benchmarks.run
python -m benchmarks.run --no-ollama --repeat 1 --out /tmp/intentforge-bench
python -m benchmarks.audit_training
```

## Corpus

Version 1 contains a small, manually composed seed corpus and a separate,
seeded synthetic corpus. Both are synthetic in provenance. The manually composed
examples were written for this evaluation with AI assistance, with no claim of
a human-written or field-sourced data collection. Each case includes source,
accepted and rejected references where available, intent, a compiler-support flag,
a mutation family, provenance and an evaluation split. The benchmark never uses
these cases to train, tune, or replace the shipped model.

The runner compares normalized token templates of every input and accepted
reference against both archived training files. It normalizes identifiers and
literal values while retaining the token structure and lexical errors. An
overlap aborts the run. The evaluation mutation families use new source templates
and include cases outside the generator's repair classes. Shared concepts such
as missing delimiters are intentional. Full reconstruction of historical
training membership is unavailable, as the archived row count differs from
the model report.

## Modes

- **Rule-based** uses native parser recovery and compound candidates. Candidate ranking uses deterministic context and generation order with all ML scores disabled.
- **Existing ML** uses the shipped classifier, its class-conditioned generator, and the existing ranker and validator. Native syntax candidates are excluded from the proposal pool. Compiler-derived input features remain available to the classifier.
- **Hybrid** runs the default correction orchestrator with ML, native candidates, and validation. Its Ollama transport is disconnected to permit an offline comparison.
- **Ollama-assisted** runs the same orchestrator with the real local transport when discovery confirms the configured model is installed. The report records whether an inference call actually occurred.

All modes share the compiler's lexical, syntax and semantic detection. The
benchmark records faults the compiler could detect and valid syntax with known
logic faults. Unsupported Mini-C cases are recorded and excluded from metrics.
Unsupported logic faults count as misses in the overall results, with a separate
recall for compiler-detectable faults.

## Scoring

Exact correction compares raw text. Top-1 and top-3 compare the first decision
and remaining unique locally validated proposals, in rank order, with acceptable
token sequences. Those metrics use supported, unambiguous faults with a supplied
reference. The strict intent outcome also requires full syntax and semantic
validity. A compiling result is incorrect only if its token sequence matches
an explicitly rejected implementation. Unmatched or unverified proposals are
`UNKNOWN_INTENT`. Ambiguous cases are measured by automatic abstention. The
incorrect-repair denominator covers only compiler-valid top proposals that the
references adjudicate.

Compiler validity includes lexical, syntax, and supported semantic checks.
Behavioral equivalence is recorded as unverified. Mini-C has no execution oracle.
The regression count tracks unwanted change or erroneous diagnostics on known-valid
controls. Historical behavior on the separate regression suites is recorded in
the [Phase 1 results](../docs/phase1_results.md).

Latency covers the correction call only and uses wall-clock timings across the
requested repetitions. Results include mean and nearest-rank p95. Timings vary
by host. Ambiguous Ollama responses and local service latency can also vary.
Report files include per-case decisions, per-category denominators, model SHA-256,
dataset hash, and dependency versions.

- [Generated Markdown report](reports/phase1-v1.md)
- [Generated JSON report](reports/phase1-v1.json)

## Phase 1.5 extended corpus

`python -m benchmarks.run --no-ollama` now evaluates the complete 111-case
corpus and writes `phase1-v2.json` and `phase1-v2.md`. The 32 historical
cases and the original v1 reports are retained. The 79 cases in
`phase_1_5_holdout` were AI-assisted and reviewed for this evaluation. They
were frozen before scoring and never used to tune the classifier. Metrics
are reported both overall and by split.

```sh
python -m benchmarks.review_corpus
python -m benchmarks.run --no-ollama --check
python -m benchmarks.run --no-ollama --corpus holdout --out /tmp/intentforge-holdout
python -m benchmarks.run --no-ollama --corpus historical --out /tmp/intentforge-historical
```

Corpus review checks identifiers, split membership, source validity and
references, expected input/return vectors, exact archived-template overlap,
and normalized token four-gram near duplicates. Similarity exceptions require
a documented review. The report records a dataset digest and the bundled
artifact digest. The consistency command checks decision stability and report
serialization while disregarding wall-clock samples.

Version 2 also measures policy decisions and actual offline workbench
options. The workbench measure covers hybrid only and counts a known-intent
case when an accepted reference is offered in its existing review or
apply workflow. A safety holdout is a case flagged for review with no
automatic change. Provider rejections are counted separately. The
legacy repair ranking metrics continue to use proposals for the first
diagnostic. Complete applied outputs are measured separately so a partial
edit to a multi-error program cannot count as a recovered intention.

An optional `behavior` object declares an entry function and input/return
vectors. It can be evaluated through an injected `BehaviorOracle` in tests
or by a future isolated engine. Current benchmark runs never execute Mini-C
and report observation status separately from token matches. See the
[extended evaluation](../docs/phase1_extended_benchmark.md).
