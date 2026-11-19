# Shared Mini-C and Clang evidence

`POST /v1/compiler-evidence` returns schema version 1. Select Mini-C
with `{"language":"mini-c","code":"int f(){return 1;}"}`, or Clang
with `{"language":"c","code":"int f(void){return 1;}","standard":"c17"}`.
C also accepts explicitly named translation units and submitted files
within the existing limits. Provider, language, readiness, AST completeness
and unsupported capabilities are explicit.

Each unit includes native AST node kinds, numeric node and scope IDs,
parent links, declaration references, declared and canonical types,
optional signatures, and structural control-flow nodes. IDs are local to
the response unit. Control-flow nodes are observations and carry no
execution or reachability guarantee. Each diagnostic may include an
editor span, related ranges, and child notes. C macro expansion and
spelling locations are retained where libclang exposes them.
Mini-C character offsets are converted to UTF-8 byte offsets and
one-based UTF-16 columns. Missing locations are nullable.

The workbench's new shared inspector shows comparable evidence counts
and diagnostic navigation for each provider. It invalidates on source,
language, or standard changes. Native inspectors and repair review are
still available. C repair, linking and execution are outside this
release. Contract tests cover native API parity, multiple files, macro
evidence, scopes and Unicode source locations.
