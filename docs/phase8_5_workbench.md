# Phase 8.5 workbench

Select **Phase 8.5 branch-aware repair** in the Intention engine menu. Choose
supplied examples and enter the function name, expected returns and any
optional input bounds. The result shows the typed requirements, original
branch coverage and reaching definitions or the bounded loop summary. Expand
the coverage section to see how a modeled edit changes the sampled paths.

To observe behavior, open **Interactive behavioral verification**, enable
candidate comparison and select the same opt-in profile. When the restricted
local worker is available, supply trusted vectors and run verification.
Candidate review includes the original and proposed source, evidence, and
both edit locations for a coordinated proposal. One explicit approval applies
the entire candidate.

The following captures come from the real Chromium Playwright scenarios.

- [Joined branch and reaching definitions](../audit/phase85/joined-branch-evidence.png)
- [Bounded counting summary](../audit/phase85/bounded-loop-evidence.png)
- [Static coordinated edit preview](../audit/phase85/two-site-static-preview.png)
- [Verified coordinated approval](../audit/phase85/verified-coordinated-approval.png)
