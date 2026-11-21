# Path sensitivity

Each CFG block can hold up to eight states. A state tracks reaching-definition sites and facts by lexical binding identity. Supported atomic conditions include boolean literals and variables, and pure integer comparisons to constants with inequality, equality and exclusion. Writes invalidate facts. Calls conservatively invalidate global facts. Unknown conditions keep both modeled outcomes. Loop entry, exit, back, break and continue edges follow the Phase 6 CFG.

Each return exposes feasibility, per-state direct reaching definitions, and possible upstream definitions from conservative slices. The earlier CFG remains available for broader control flow. A cutoff leaves unvisited returns unknown. A modeled return indicates consistency in the abstract domain, which can still admit infeasible concrete executions.

The state cap, 1,200 path transfers per function, Phase 6 CFG limits and shared analysis deadline bound the scan. Unsupported relationships include compound predicates, affine assignments, arbitrary aliasing and relational invariants between variables. Tests cover contradiction, shadowing, possible writes and path exhaustion.
