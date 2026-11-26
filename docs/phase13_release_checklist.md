# Demo release candidate checklist

Suggested review identifier: **0.13.0-rc.1**. A maintainer can choose the version and publication date after reviewing this branch.

## Changelog draft

- Added a discoverable demo picker entry, an ambiguity walkthrough, and a development/production Chromium check that exercises Monaco, same-origin API calls and source-bound approval.
- Exposed an opt-in Phase 13 profile with bounded empty-prefix and scalar endpoint proposals. Consolidated historical evidence serialization.
- Archived pinned upstream pairs, original-language replays, leakage decisions, like-for-like profile comparisons and fresh private-worker observations.

## Review gates

- [x] Start the application with the supported Python and Node versions and follow the [demo](phase13_demo_guide.md).
- [x] Exercise development and built preview with a reachable and unavailable API.
- [x] Inspect real source diffs and verify source-bound approval.
- [x] Record frozen inputs, separate cohorts, quarantine and limitations.
- [ ] Verify a real private forwarded Codespace and the HTTP/2 incident.
- [ ] Obtain independent adaptation review.
- [ ] Maintainer review of the PR, passing head checks, version decision and explicit publication authorization.

Existing hosting can serve the frontend and analysis API. Use the private Linux worker for a presenter-controlled verification demo. Reviewers can reproduce both modes locally with freely available dependencies. Deployment, tagging, release publication and merging require separate decisions. [Security and hosting](phase13_security_review.md)
