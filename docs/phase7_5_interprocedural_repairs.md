# Interprocedural repairs

The scalar helper witness checks reachable blocks, bounded calls, lexical reaching definitions and the transitive global-effect summary. It supports nested scopes, initialized scalar locals, effect-free arithmetic, bounded scalar branches and up to two levels of calls to witnessed helpers. A direct identity wrapper can forward a unique local alias. Arithmetic and execution limits remain observable in the VM.

Two uniquely traced recursive terms can reach a single combining operator through temporaries, identity wrappers or a small literal coefficient. Candidate edits change only that operator. The surrounding calls, their order, their coefficients and their computation stay in place.

The helper-argument rule requires two sibling calls to a witnessed helper, one repeated contributing parameter position and exactly one unused caller parameter. Its examples must vary that parameter while holding the others fixed and yield different expected outputs. Both possible call sites may remain plausible. Mutation, arrays, unknown calls, multiple reaching local definitions and arbitrary source inlining are outside the modeled repair.
