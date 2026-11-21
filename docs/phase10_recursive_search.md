# Recursive search

An interval ties two lexical endpoints and a recognized midpoint to a fixed local array. Supported inclusive and half-open branches are inferred from the guard and the endpoint transitions. Calls preserve the other arguments, stay within their admitted bounds and strictly shrink the active interval. Recursive projection is capped at eight frames.

The model can adjust an existing caller endpoint. It can also insert an empty-interval branch when a consistent negative expected absence result, two distinct hits and at least two failed original samples support it. The independent lower-bound case returns an endpoint when the interval collapses and needs a different contract. The half-open, singleton and correct inclusive controls preserve their supplied behavior.
