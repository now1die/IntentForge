# Recursion and base cases

The repair scope is a direct one-parameter integer recursion with an initial guarded return and one supported self-call in the fallback result. A self-call passing the same parameter under an ordered guard can yield a unit step toward that guard. The new expression changes one argument and preserves the existing recurrence. The intended recurrence and domain remain assumptions.

A singleton equality guard can yield an adjacent base input when a supplied vector establishes its domain and a unit step otherwise moves away. The edit adds only that supplied point. An expected return for the precise singleton input can support a replacement literal if the original is a scalar literal of the same type. The program is compiler-validated and can then be executed on the existing worker.

Mutual cycles and possible missing returns are reported as evidence. Synthesis abstains on mutual recursion, multiple call sites, general base-case structures and unknown direction. A call-depth failure is an execution limit. These analyses establish no general termination result.

```sh
python -m pytest -q tests/test_phase6.py -k 'recursive or singleton or behavior_gateway'
```
