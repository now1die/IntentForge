# Generalization analysis and provenance

Each partition uses a different set of program families. There are
27 training, 10 selection, 8 calibration, 6 development and 26 final
families, one case per family. The examples vary control flow,
nested counting, helper signatures, array usage, numeric operations,
shadowing, globals, early exits and ambiguity. Earlier corpora and
legacy training material never enter v3 training or model selection.
The audit checks exact source, normalized tokens, normalized ASTs
and near-duplicate input and reference pairs at a threshold of 0.94.
It found no cross-partition matches after excluding overlapping
fixtures during data construction.

Three final programs adapt descriptions from Exercism
problem-specifications at commit `4812c213a2647e2034ad5ac78155ce9265cdd171`
under the MIT license. The corpus records the exact description and
license URLs. They use original Mini-C implementations for a
three-digit Armstrong test, numeric resistor band encoding, and one
cell of a numeric slice. Other cases are original IntentForge
exercises. The final suite was written and frozen after committing the
engine, model and selection rules and before scoring. Its labels
are authored references. No independently collected blind corpus or
external grading was available.

The final code-only candidate pool included no correct reference for
any of the three external adaptations. Different algorithms, broader
English, and ambiguous semantics remain gaps. The strongest finding is
improved candidate coverage on the authored cases that match supported
structural evidence.

Code-only v3 alerted on 5/14 known logic faults, compared with 1/14 for
Phase 2.5 learned. One of six confirmed valid controls alerted, compared
with zero for Phase 2.5 learned. Alert precision was 5/6 on the labeled
valid inputs. The false positive returned a computed value above a
threshold and deliberately used a different fallback after updating a
parameter. This remains a plausible but incorrect peer analogy.
The interval for logic recall was approximately 16–61%. Both ambiguous
inputs avoided a definitive repair and all 26 cases avoided automatic
changes. A duplicate pure guard may be reported as an observation with
no candidate. The code-only UI shows the underlying evidence, missing
specification and behavioral verification status. Its control-flow
observations are local and incomplete.
