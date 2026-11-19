FROM python:3.12-slim-trixie@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b

RUN --mount=type=bind,target=/build --mount=type=secret,id=pip_ca \
    set -eu; \
    apt-get update; \
    apt-get install -y --no-install-recommends libclang1-19 libseccomp2; \
    rm -rf /var/lib/apt/lists/*; \
    if [ -f /run/secrets/pip_ca ]; then export PIP_CERT=/run/secrets/pip_ca; fi; \
    pip install --no-cache-dir fastapi==0.135.1 uvicorn==0.41.0 clang==19.1.7; \
    cd /build; \
    for file in analysis_evidence/*.py clang_backend/*.py backend/app/*.py backend/app/routes/*.py; do \
        install -D -m 0644 "$file" "/app/$file"; \
    done

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    INTENTFORGE_CLANG_MODE=isolated \
    INTENTFORGE_LIBCLANG=/usr/lib/llvm-19/lib/libclang-19.so.1
USER 10001:10001
ENTRYPOINT ["python", "-m", "uvicorn", "backend.app.clang_service:app", "--uds", "/tmp/intentforge-clang.sock", "--no-access-log"]
