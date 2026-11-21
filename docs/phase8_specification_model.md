# Specification model

Phase 8 validates the selected function and its integer or Boolean signature. Expected outputs are a separate collection from input-only partial observations. It checks input arity, exact scalar types, signed 32-bit ranges, conflicting expectations and source identity. Invalid source yields incomplete compiler evidence. Unsupported signatures and insufficient arithmetic examples have distinct statuses.

An optional domain is a positional list of inclusive integer bounds or null entries for unrestricted scalar parameters. Boolean arguments require null when a domain is supplied. Every input and expected result keeps its type. The domain restricts admission of specified examples and worker probes. It gives no expected output for unlisted inputs. The report identifies expectation provenance and records checked integer arithmetic and division assumptions.

The examples endpoint accepts partial inputs without expected outputs. The runtime contract keeps original mismatches, agreement, unsupported execution, limits and multiple matching candidates distinct.
