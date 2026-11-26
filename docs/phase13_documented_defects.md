# What each admitted defect measures

Each row is a finite Mini-C adaptation of a documented upstream revision. The private worker confirmed a mismatch for all five originals.

| Family | Observation and repair outcome | Missing capability or limiting evidence |
| --- | --- | --- |
| Empty maximum | An empty prefix produced encoded IndexError (−98). The reference returns encoded ValueError (−99). An earlier guard returned −99 and passed holdout while leaving the old guard in place. | Behavioral recovery only. Supplied empties establish this scalar convention over the tested inputs. |
| Empty TimSort | An empty run produced encoded IndexError (−81). A scalar change to −82 matched the reference and held-out inputs. | All five profiles recovered this small adapter. It observes only the first element for runs of size one or two, or the empty result. |
| Decimal digits | The old loop returned zero for zero or a negative argument. | Needs signed-magnitude normalization and a loop that counts zero once. The new one-site grammar cannot express the coordinated reference. A sign and termination contract would support further work. |
| Combination domain | Negative n produced a count where the corrected function raises an encoded domain error. | A guard is syntactically expressible, but the entry grammar requires a verified array-prefix relation. This recursive count needs an input-domain and error contract for its wrapper. |
| Hex green channel | The adapter selected the wrong adjacent pair of nibbles from a six-digit string. | A literal replacement can express the reference. No active mechanism relates the initialized offset to the required channel in this weighted two-cell read. A channel layout contract would identify the origin. |

For the last three families no candidate reached compiled discovery or holdout verification. The reports expose emitted candidates and their outcomes, without a per-trial trace of internal projection rejection. [Pinned files and revisions](../benchmarks/phase13_data/revisions.json) · [Original observations](../benchmarks/reports/phase13-upstream-v1.json)
