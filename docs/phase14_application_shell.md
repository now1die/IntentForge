# Shared workspaces

The header and sidebar use the same hash route for Compiler, Intention, Research Lab and Examples & Learning. Desktop keeps both navigation surfaces and a fixed-angle burgundy header edge. At narrower widths the compact sidebar remains keyboard accessible. Settings reports backend and worker availability and refreshes both. Help opens the learning path.

A single Monaco editor is mounted across the main workspaces. The source, language, cursor and analysis stay in the session during navigation. The expected-behavior panel stays mounted so its inputs survive a route change. Loading an example asks before replacing modified source. The historical workspace opens separately from Research Lab.
