# Constraint generation

The checked projection follows a linear CFG through initialized scalar declarations and a single value return. Reads use lexical compiler binding identities. It carries arithmetic terms and the intermediate expressions that must remain evaluable, including helper arguments and local initializers. The existing function summaries screen mutable global effects and uncertain callees.

The engine substitutes only supplied scalar inputs and checks integer arithmetic, signed division and remainder, and overflow obligations. At least two distinct input tuples are required for new arithmetic synthesis. An original that already satisfies the modeled examples adds no new arithmetic candidates. A checked failure, unsupported expression, insufficient evidence or exceeded work budget produces its own status. Actual Mini-C behavior is observed only in the worker.
