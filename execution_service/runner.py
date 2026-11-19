"""Resource-accounted process transport used only by the private VM service."""
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
from tempfile import TemporaryFile
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
MAX_OUTPUT = 96_000
WORKER_TIMEOUT = 3.0


class RunnerFailure(Exception):
    def __init__(self, status):
        self.status = status
        super().__init__(status)


def run_worker(action, payload=b"", *, timeout=WORKER_TIMEOUT, limit=MAX_OUTPUT):
    command = [
        sys.executable, "-I", "-B", "-c",
        "import sys; sys.path.insert(0, sys.argv[1]); from execution_service.worker import main; main()",
        str(ROOT), action,
    ]
    with TemporaryFile() as source:
        source.write(payload)
        source.seek(0)
        return collect(command, source, timeout, limit)


def collect(command, source, timeout, limit):
    deadline = monotonic() + timeout
    env = {"LC_ALL": "C", "PATH": os.defpath, "TMPDIR": "/tmp", "OPENBLAS_NUM_THREADS": "1"}
    try:
        with subprocess.Popen(command, stdin=source, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              env=env, start_new_session=True, close_fds=True) as worker, selectors.DefaultSelector() as poll:
            complete = False
            try:
                poll.register(worker.stdout, selectors.EVENT_READ)
                output = bytearray()
                while True:
                    remaining = deadline - monotonic()
                    if remaining <= 0 or not poll.select(remaining):
                        raise RunnerFailure("deadline_exceeded")
                    chunk = os.read(worker.stdout.fileno(), min(16_384, limit + 1 - len(output)))
                    if not chunk:
                        break
                    output.extend(chunk)
                    if len(output) > limit:
                        raise RunnerFailure("worker_unhealthy")
                status = worker.wait(timeout=max(.001, deadline - monotonic()))
                if status == -signal.SIGXCPU:
                    raise RunnerFailure("deadline_exceeded")
                if status:
                    raise RunnerFailure("worker_unhealthy")
                result = json.loads(output)
                if not isinstance(result, dict):
                    raise RunnerFailure("worker_unhealthy")
                complete = True
                return result
            finally:
                if not complete:
                    try:
                        os.killpg(worker.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
    except subprocess.TimeoutExpired:
        raise RunnerFailure("deadline_exceeded") from None
    except (OSError, ValueError, RecursionError):
        raise RunnerFailure("worker_unhealthy") from None
