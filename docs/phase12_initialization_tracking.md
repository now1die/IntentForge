# Initialization tracking

The Mini-C VM initializes entry parameters and leaves local declarations without initializers, including array cells, uninitialized. The state pass tracks scalar declarations, definite direct stores, unknown-index stores and branch and loop joins. An unknown-index store makes each tracked cell possibly initialized. Literal-index stores establish only the named cell. Reads with competing effects in the same statement are withheld because statement-level ordering cannot establish their incoming value.

Initialization facts concern paths that reach the reported operation. Helper returns can initialize a target after a successful assignment, but the pass has no general call-result or global-memory summary. Structure fields, pointers, array parameters, and dynamic storage are outside this pass.
