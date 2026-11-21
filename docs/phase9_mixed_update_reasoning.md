# Mixed scalar updates

Phase 9 admits up to two loop-carried integer locals besides induction. A
bounded transfer models assignments, additions and subtractions, increment
and decrement, pure local temporaries and supported conditional branches.
Sequential expression constraints preserve when a read sees a prior update.
Short-circuit and conditional selection evaluate only the active branch.

Each supplied vector records the sampled step, iteration count and exit
state. Return expressions can combine both carriers. The CFG/body limit is
ten blocks. Global or array effects, invocation of helpers inside the loop,
unmodeled statements, a third carrier and nested loops cause abstention.
