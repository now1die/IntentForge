# Reaching definitions and bindings

The worklist analyzes a may-reaching set of binding and block pairs. Entry seeds originate at parameters, globals and potentially unavailable locals. A guaranteed direct scalar write kills prior definitions of the same binding. Conditional expression writes, global effects of calls and array element writes remain possible writes. Shadowed names refer to separate lexical IDs. Statement-level uses and definitions conservatively merge effects within an expression, including possible short-circuit outcomes.

Return slices follow observed definition-site reads through the reachable graph and retain their source locations. Conditions retain their own reads and locations. Array cells share a binding and call effects conservatively include globals. Scope lifetime and call effects are approximated. The implementation does not perform path-sensitive symbolic execution or infer formal control dependence for each returned value.

Analysis admits up to 1,200 AST nodes, 16 functions, 220 graph blocks and 440 edges per function, and 450 blocks for the program. Each function has up to 1,800 worklist transfers and each return slice follows up to 64 definitions. The semantic pass uses a cooperative 350 ms deadline inside the original analysis budget. Limited passes report incomplete evidence.

```sh
python -m pytest -q tests/test_phase6.py -k 'reaching or unknown or limit'
```
