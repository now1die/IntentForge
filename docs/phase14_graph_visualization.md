# Control-flow visualization

Research Lab requests `include_context` on the existing intention endpoint. It consumes the function's backend-supplied CFG with exact block identities, reachability, source spans and directed edge kinds. Layout groups blocks by distance from Entry, ignoring loop-back edges during placement. All returned edges remain present, including back edges, return edges and conditional directions.

Select a block with the mouse or keyboard for adjacent edges, reachability and a source selection action. Drag the canvas to pan. Zoom, Fit and Reset use explicit controls. The Compiler overview renders a compact form of the same graph. Graph construction remains bounded by the existing engine and available only when the requested profile returns a Mini-C CFG.
