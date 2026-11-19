# Clang integration

The optional binding is `clang==19.1.7` with the libclang 19 C API.
Verification used Debian libclang 19.1.7. The worker probes the actual
library and parses a C23 fixture before enabling capability. C99, C11,
C17 and C23 are selectable, with C17 the default.

```bash
python -m pip install -r requirements.txt -r requirements-clang.txt
export INTENTFORGE_CLANG_MODE=isolated
export INTENTFORGE_LIBCLANG=/path/to/libclang-19.so.1
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
npm --prefix frontend run dev
```

`GET /v1/c-analysis/capability` reports the worker's readiness, supported
standards and unavailable operations. `POST /v1/c-analysis` accepts a
single editor buffer, or a mapping of relative names with an explicit
entry list.

```json
{"files":{"inc/types.h":"typedef int Count;","main.c":"#include \"inc/types.h\"\nCount c;"},"translation_units":["main.c"],"standard":"c17"}
```

Submitted headers resolve by project-root path or eligible same-directory
names. The worker has no implicit host SDK, and directory traversal in
include spellings is outside the supported virtual project layout.
Supply required declarations as headers. Translation units are checked
individually and are never linked. Invalid JSON/schema uses HTTP 422,
oversized transport uses HTTP 413, and bounded analysis outcomes use
the typed response status. Clang diagnostics use libclang category and
warning-option APIs. A mixed or unclassified error group can return
`compiler_errors`. AST recovery may produce a partial tree. Macro
cursors and expansion positions are preserved where available, with
spelling ranges returned when Clang supplies a distinct representable
range. `#line` does not change physical editor locations.

The workbench's C selector uses the same Monaco editor and displays
diagnostics, an expandable cursor tree and declarations with type and
scope information. Edit, standard changes and language switches
invalidate the response. The workbench sends one editor file. Multi-file
requests are supported through the API.
