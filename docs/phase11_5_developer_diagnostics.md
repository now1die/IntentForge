# Developer diagnostics

Run `python -m scripts.doctor` with the Python environment active and both servers started. Use `--frontend-port 4173` for preview or `--backend-port` for a custom local listener.

The command checks Python and Node versions, required packages, backend health and sample compiler output, frontend HTML and entry JavaScript, and the same-origin API bridge. It reports whether an API override is set without exposing its value. Worker availability, disconnection, capacity and analysis-only mode have distinct results. Missing optional interactive execution does not fail basic readiness. The CLI checks loopback, and browser DevTools capture remote forwarding or HTTP/2 errors.
