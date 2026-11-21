# Range-origin dependencies

A literal origin can be rebound to a visible, initialized integer parameter or
local whose definitions reach loop entry. The search excludes mutable loop-body
bindings and uses a short deterministic list of source-local alternatives. At
least two failing examples must be repaired and the sampled origins must vary.

The cohort includes deliberate zero-based and one-based ranges, descending
ranges and derived starts. A starting value can come from a supported pure
helper. Synthesis does not introduce scans or derive missing endpoints from
scratch, which explains the shifted missing-number abstention.
