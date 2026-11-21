# Fixed-array semantics

The projection records the compile-time length, scalar element type, declaration location and lexical storage identity of each supported local array. Each frame starts with its own cell facts. A checked write initializes a cell. A read requires that the evaluated signed index be in the declared extent and that the relevant cell have an initialization fact.

The UI highlights invalid index observations with their input and source site. Observations aggregate the sampled minimum and maximum by site, access kind and input. The response includes up to 80 sampled access records. Local scalar cells and fixed bounds provide the supported abstraction. Global storage, aliases and unrestricted memory have no Phase 10 projection.
