# Codespaces and startup verification

Local checks used Python 3.12.14 and Node 24.22.1. Backend port 8000, Vite development port 5173 and production preview port 4173 passed the compiler health and same-origin bridge checks. Chromium mounted Monaco, reloaded the built workbench and ran analysis through `/api/analyze`. Exact simulated Codespaces forwarded hosts worked for both frontends. Other hostnames were rejected with HTTP 403.

GitHub Codespaces discovery returned HTTP 403, `Resource not accessible by integration`. Hosted private forwarding, real HTTPS and the reported HTTP/2 asset incident remain unverified. To check an existing Codespace, start the services from the [setup guide](phase11_5_codespaces_setup.md), inspect the browser Network protocol and status for the entry script, lazy chunk, fonts, Monaco worker and `/api/health`, then hard reload and run Analyze. Keep forwarded ports private.

Run `python -m scripts.doctor` with the dev server active and `python -m scripts.doctor --frontend-port 4173` with preview. The diagnostic distinguishes reachable HTML from its entry script, backend reachability from compiler readiness, proxy access and optional execution status. It avoids printing environment credentials and forwarding URLs.
