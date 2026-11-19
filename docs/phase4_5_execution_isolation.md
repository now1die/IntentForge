# Reproduce the verified local execution profile

Use Docker on Linux and an unprivileged host account. Install the main application's dependencies separately with `python -m pip install -r requirements.txt`. Build and run the worker from the repository root. Keep the socket directory private and use the same unprivileged UID for the gateway and the service.

```sh
docker build -f deployment/minic.Dockerfile -t intentforge-minic:local .
socket_dir=$(mktemp -d)
container=$(docker run -d --network none --read-only --cap-drop ALL \
  --security-opt=no-new-privileges --memory 512m --memory-swap 512m --cpus 1 --pids-limit 48 \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=16m,mode=1777 \
  --mount "type=bind,source=$socket_dir,target=/run/minic" --user "$(id -u):$(id -g)" \
  intentforge-minic:local)
export INTENTFORGE_VM_GATEWAY=isolated-local INTENTFORGE_VM_SOCKET="$socket_dir/minic.sock"
curl --fail --unix-socket "$INTENTFORGE_VM_SOCKET" http://localhost/internal/capability
```

The capability response must report `available` with boundary `isolated-local-v1`. Retry the check after startup if the socket is still being created. From the same environment, either run the tests or start the development API.

```sh
python -m pytest -q tests/test_phase45_isolation.py
python -m benchmarks.phase45_isolation
docker exec -i "$container" python - < deployment/minic_metrics.py
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

Run the workbench with `npm --prefix frontend ci` and `npm --prefix frontend run dev` in a separate terminal. When finished, stop Uvicorn, then run `docker rm -f "$container"` and `rmdir "$socket_dir"`. See [security controls](phase4_5_security.md) for the capability checks.
