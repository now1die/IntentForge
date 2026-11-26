# Startup and the forwarded-host incident

Python 3.12.14 and Node 24.22.1 ran FastAPI at 127.0.0.1:8000. The doctor reached the compiler, entry JavaScript, frontend HTML, same-origin API and isolated capability in development (5173) and built preview (4173). Chromium reloaded with cache disabled, mounted Monaco, opened examples, submitted real analysis, reviewed the source diff and approved it. The diagnostic script also requested the editor worker through Monaco's configured factory and evaluated in the started worker.

| Browser target | Backend | Observed result |
| --- | --- | --- |
| Development, 5173 | Available | Connected, reviewed change applied, development worker loaded |
| Preview, 4173 | Available | Connected, reviewed change applied, built worker asset loaded |
| Development, 48130 | Unavailable proxy target | Backend offline, example source and editor loaded |
| Preview, 48131 | Unavailable proxy target | Backend offline, example source and editor loaded |

To repeat, use the README setup, install Chromium with `cd frontend && npx playwright install chromium`, then run `node frontend/scripts/verify-demo.mjs 4173` from the root against the preview. Stop FastAPI and repeat with `--offline`. The same script accepts 5173. Set `INTENTFORGE_DEMO_CAPTURES` to a directory to save the actual source diff.

**Hosted validation remains blocked.** Listing repository Codespaces returned HTTP 403, `Resource not accessible by integration`. There was no authorized forwarded HTTPS URL on which to measure status, protocol, failed asset requests, browser console, worker requests or health. The original white-screen HTTP/2 incident remains open. The supported hosted setup uses private port forwarding and a same-origin frontend route. [Codespaces procedure](phase11_5_codespaces_setup.md)
