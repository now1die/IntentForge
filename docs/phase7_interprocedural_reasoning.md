# Interprocedural reasoning

The existing transitive-effect summaries and lexical argument records feed an optional scalar-helper witness. It describes bounded single-return arithmetic over literals and parameters, with up to two levels of helper calls and no mutable global effects. Unknown or incomplete summaries and cycles are excluded. The witness records conservative parameter dependence and a direct identity-parameter form. Checked arithmetic can still fail at runtime.

The extended recurrence recognizer can edit the unchanged guarded parameter of a direct self-call wrapped by a witnessed helper. It can also propose recurrence operator alternatives inside a single-argument identity helper when examples guide the review. Helper bodies remain unchanged. General nonunit step synthesis, mutual recursion, helper-mediated local recurrence temporaries, arbitrary arithmetic and side-effecting helper repairs remain unsupported.
