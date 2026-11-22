# Run in GitHub Codespaces

Use Python 3.12 and Node 20.19 through 24. Start the backend from the repository root:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Start the frontend in another terminal:

```sh
npm --prefix frontend ci
npm --prefix frontend run dev
```

Forward **5173** with **Private** visibility in the Ports panel and open its forwarded URL. The frontend sends same-origin requests under `/api`. Vite connects to FastAPI on server loopback at port **8000**. A private forward for 8000 is useful only for direct API inspection. Use the default API base. When changing the backend port, set `INTENTFORGE_BACKEND_PORT` for Vite and restart it.

To verify production assets, keep FastAPI running and forward preview port **4173** privately:

```sh
npm --prefix frontend run build
npm --prefix frontend run preview
python -m scripts.doctor --frontend-port 4173
```

For an asset failure, inspect the browser Network and Console panels, disable cache for one reload and compare development with preview. The entry module should return JavaScript and `/api/health` should return JSON. Record the exact failing URL, status and browser protocol if the HTTP/2 error recurs.

Local development, preview and derived forwarded hosts were verified. The GitHub integration could not list Codespaces because the API returned HTTP 403. The actual forwarded HTTPS session and the reported HTTP/2 failure remain unverified. Analysis works with the optional restricted worker disconnected.
