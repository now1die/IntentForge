# Documented external defects

| Family | Upstream correction | Adaptation |
| --- | --- | --- |
| Lower-end primality | Reject nonnegative inputs below two | Replace the square-root bound with its equivalent small-positive integer square comparison. [Upstream fix](https://github.com/TheAlgorithms/Python/commit/36828b106f7905ecc0c0776e40c99929728a91a9) |
| Last product window | Extend the exclusive outer bound by one position | Decode four scalar chunks to a local digit array. Preserve the missed last window and the no-window sentinel on the checked Mini-C range. [Upstream fix](https://github.com/TheAlgorithms/Python/commit/9417091dabf9d8e9ebec078942a2fbba0966e42f) |
| Missing number in a shifted range | Derive bounds from the values instead of assuming zero | Accept five scalar values and reproduce XOR with an arithmetic helper over the declared nonnegative domain. [Upstream fix](https://github.com/TheAlgorithms/Python/commit/3ecad36f92d26676cc73276553cd99763b025b33) |

The compiler and VM confirmed that each defective adaptation fails on
discovery and that its corresponding reference agrees with independent expected
outputs on both suites. The score measures repairs on these adaptations.
A documentation-only gcd change and defects requiring exception contracts or
text APIs were not admitted.

The restricted worker confirmed all three discovery mismatches. Phase 9
emitted no candidate for any of the adapted defects. This made the external
subset a check on where the current grammar abstains.
