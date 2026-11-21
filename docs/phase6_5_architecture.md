# Phase 6.5 architecture

Public intention analysis and local verification opt in with engine version `65`. The compiler, Phase 6 CFG, lexical binding index and path-insensitive return slices supply the inputs. Phase 6.5 adds bounded path states and call contracts, then applies the new synthesis and precision rules before compiler validation. Earlier profiles use their existing rules and responses.

Static evidence is available through `program_analysis.phase65`. Each candidate carries a source snapshot, provenance, evidence basis and explicit approval requirement. Behavioral verification uses the existing private worker protocol and preserves static rank alongside behavioral review order. The static endpoint makes no VM calls.
