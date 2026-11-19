# Phase 4 supported Mini-C language

The VM evaluates the existing validated AST. The compiler supplies the
grammar, types and scope rules. The VM defines execution policies where
the compiler has no runtime specification.

| Category | Capability |
|---|---|
| Values | Signed 32-bit checked integers and booleans. Void is supported for internal helpers. |
| Expressions | Arithmetic, relational and equality comparisons, short-circuit Boolean operations, unary signs and negation, assignment and compound assignment, prefix and postfix updates. |
| Bindings | Global and block variables, parameter passing by value, lexical scope and declaration shadowing. |
| Control flow | Blocks, if/else, while, for, break, continue, return, direct function calls and bounded recursion. |
| Arrays | One-dimensional integer and Boolean arrays, evaluated sizes, checked indexing and writes. Arrays stay in their owning scope. |
| Excluded | Float, char and string constructs, bare declarations as control-statement bodies, indirect calls, and entry points that return void. |
| Outside Mini-C VM | Clang/full C, host functions, pointers, external I/O, dynamic loading and native execution. |

Non-runtime language features are rejected before execution if they
occur anywhere in the validated AST. This prevents an unsupported
branch from being silently admitted by a narrow test vector. Ordinary
functions can call internal void helpers and ignore their result.
