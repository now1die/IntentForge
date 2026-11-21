# Phase 9.5 architecture

Engine 95 is opt-in. The existing compiler supplies typed expressions, lexical
IDs, control-flow edges and reaching definitions. The new projection lowers
a closed grammar into scalar terms and bounded transfer facts. It emits
source-local proposals that must pass the existing compiler gate.

The workbench shows entry constraints, projected loop indices and exits. The
gateway maps public profile 95 to private execution profile 8. Source
identity, isolated verification and explicit approval use the existing contracts.
