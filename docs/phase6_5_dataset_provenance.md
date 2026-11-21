# Dataset provenance

The [freeze](../benchmarks/phase65_data/manifest-v1.json) indexes 28 rows across development, model selection, calibration and final evaluation, grouped by algorithm family. Project authors injected localized faults. Expectations come from independent executable references using arithmetic, Python integer power, products and checked sequences. The evaluator separately verifies each reference and correct control on the Mini-C oracle, and confirms every admitted injected fault violates at least one supplied expectation.

Three adapted algorithm families originate in MIT-licensed TheAlgorithms/Python at `30507bbe41397065728167fb09aa820f9fce8dc7`. The upstream bytes, license and SHA-256 digests are recorded locally. Double factorial was quarantined. The admitted external adaptations are nonnegative integral power and one-based Sylvester terms with a bounded integer domain. A fault may have other valid repairs beyond its exact reference. Those outcomes are reported separately through test agreement and probe observations.

The adjudication is internal. The executable references are independent of the candidate generator. There was no external human review.
