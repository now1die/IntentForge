# Phase 3 architecture

The Mini-C compiler, its AST, lexical scopes, analysis routes, model
artifacts and repair workflow retain their existing contracts. C mode
uses separate routing, capability discovery, analysis state, and
Monaco markers. Both modes share the editor and layout.

`clang_backend/contract.py` defines the analysis evidence contract.
Files have request-relative identifiers. A span has an inclusive start
and exclusive end, physical line, editor column in UTF-16 units, and
UTF-8 byte offset. Diagnostics carry severity, category, warning option
where available, related ranges, and child notes. Clang cursors expose
provider-specific kind and a per-unit ID, optional parent and lexical
scope IDs, declaration flag, optional reference to a visible declaration,
display and canonical types, and optional function signature fields.
The scope ID denotes the nearest observed scope cursor. It is an evidence
link, not a complete C name-lookup representation.

Null means the source cursor or relation was unavailable, external,
or could not be represented exactly. AST availability distinguishes a
populated AST, partial recovery, and no AST. IDs are relative to a
translation unit and a single response. Future intention consumers can
use these optional fields without converting the Clang AST into a
Mini-C AST. Existing Mini-C rankers do not run on C input.
