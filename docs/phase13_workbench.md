# Workbench changes and regression coverage

**Explore demo examples** opens the example picker from the workbench. The picker labels its Mini-C programs as authored and supplies separate JSON formats for intention examples and interactive vectors. The added interpolation case demonstrates a choice that needs another expectation. Existing compile errors, load and offline states remain part of the same workspace.

Phase 13 is selectable in static analysis and in private verification. Its newly generated candidates carry a Phase 13 origin. The inherited semantic-state facts still appear under the Phase 12 evidence heading. A proposed change shows evidence, counter-evidence, a source diff and an explicit approval action.

Chromium coverage includes navigation from the new link, loading the ambiguous example, compiler views, current-source approval, stale-vector invalidation, abstention and private verification. The production smoke script additionally checks a hard reload and Monaco's worker factory. [Demo steps](phase13_demo_guide.md) · [Dev screenshot](../audit/phase13/diff-5173.png) · [Preview screenshot](../audit/phase13/diff-4173.png)
