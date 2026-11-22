# Adjacent-array reasoning

The finite abstraction records two cell indexes and values when a comparison actually evaluates both checked operands. It recognizes consecutive constant offsets of one lexical index and neighboring literal cells from the same declared array. Distinct local arrays with the same variable spelling in separate scopes retain distinct identities. A candidate may repair strictness or orientation of the observed comparison.

Each read requires an in-range signed index and an initialization fact. An invalid index and a missing cell fact have separate source-located evidence. If a comparison is skipped or index evaluation fails before the read, no value is recorded for it. Aliasing and unrestricted symbolic memory remain outside the projection.
