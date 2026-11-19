FROM python:3.12-slim-trixie@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b

RUN --mount=type=bind,target=/build --mount=type=secret,id=pip_ca \
    set -eu; \
    apt-get update; \
    apt-get install -y --no-install-recommends libseccomp2; \
    rm -rf /var/lib/apt/lists/*; \
    if [ -f /run/secrets/pip_ca ]; then export PIP_CERT=/run/secrets/pip_ca; fi; \
    pip install --no-cache-dir fastapi==0.135.1 uvicorn==0.41.0 ply==3.11; \
    cd /build; \
    for file in analysis_evidence/*.py compiler/*.py vm/*.py execution_service/*.py \
        ai/intention_context.py ai/behavior_oracle.py backend/app/routes/request_body.py; do \
        install -D -m 0644 "$file" "/app/$file"; \
    done

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
USER 1000:1000
ENTRYPOINT ["python", "-m", "execution_service.launch"]
