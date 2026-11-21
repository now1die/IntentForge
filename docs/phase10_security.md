# Execution and approval boundaries

The ordinary API performs typed finite projection. Runtime verification uses the existing loopback gateway and owner-only Unix socket. The non-root Linux worker runs with a read-only filesystem, no network, dropped capabilities, seccomp restrictions, memory, CPU and process limits, wall-clock deadlines, candidate/vector caps and a shared 200,000-step budget. Public execution remains disabled. Full C remains Clang static analysis.

The private batch version set is preserved. Public profile 10 uses the existing private worker contract. Source and response identities, matching source spans and explicit atomic approval protect the apply path. A runtime fault is shown with the triggering input and source location and stays separate from a trusted output mismatch. Ollama remains optional.
