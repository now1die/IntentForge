"""Bounded process transport for the optional libclang worker."""
from dataclasses import dataclass
from functools import lru_cache
import json
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import BoundedSemaphore
from time import monotonic

from .contract import Analysis, Capability


MAX_FILES = 12
MAX_BYTES = 96_000
MAX_OUTPUT = 3_000_000
MAX_UNITS = 4
TIMEOUT = 8
WORKER = Path(__file__).with_name("worker.py")
SEGMENT = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}")
SLOTS = BoundedSemaphore(2)


@dataclass
class WorkerError(Exception):
    status: str
    detail: str


def _run(args, directory, timeout=TIMEOUT, limit=MAX_OUTPUT):
    deadline = monotonic() + timeout
    environment = {"PATH": os.defpath, "LC_ALL": "C", "TMPDIR": str(directory)}
    # Use the same Python installation, without copying application secrets into the worker.
    with subprocess.Popen([sys.executable, "-I", str(WORKER), *args], cwd=directory, env=environment,
                          stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                          start_new_session=True) as process, selectors.DefaultSelector() as selector:
        output = bytearray()
        selector.register(process.stdout, selectors.EVENT_READ)
        try:
            while True:
                remaining = deadline - monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    raise WorkerError("timeout", "The Clang worker exceeded its time limit.")
                block = os.read(process.stdout.fileno(), 65536)
                if not block:
                    break
                output.extend(block)
                if len(output) > limit:
                    raise WorkerError("request_limit", "Clang evidence exceeded the output limit.")
            if process.wait(timeout=max(.001, deadline - monotonic())) != 0:
                raise WorkerError("unavailable", "The Clang worker stopped before completing analysis.")
            return json.loads(output)
        except subprocess.TimeoutExpired:
            raise WorkerError("timeout", "The Clang worker exceeded its time limit.") from None
        except (ValueError, OSError):
            raise WorkerError("unavailable", "The Clang worker returned invalid evidence.") from None
        finally:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


@lru_cache(maxsize=4)
def _discover(enabled, library):
    if enabled != "isolated":
        return Capability(status="unavailable", detail="Clang analysis is disabled on this deployment.")
    if not library or not Path(library).is_absolute() or not Path(library).is_file():
        return Capability(status="unavailable", detail="Configure an absolute libclang 19 library path.")
    try:
        with TemporaryDirectory(prefix="intentforge-c-") as name:
            result = _run([str(Path(library).resolve()), "probe"], Path(name), timeout=4)
    except (WorkerError, OSError):
        return Capability(status="unavailable", detail="The Clang installation could not be loaded.")
    return Capability(**result)


def capability():
    return _discover(os.getenv("INTENTFORGE_CLANG_MODE"), os.getenv("INTENTFORGE_LIBCLANG"))


def _validate(files, entries):
    if (not 1 <= len(files) <= MAX_FILES or not 1 <= len(entries) <= MAX_UNITS
            or sum(len(source.encode("utf-8")) for source in files.values()) > MAX_BYTES
            or len(set(entries)) != len(entries)):
        raise WorkerError("request_limit", "Use at most 12 files, four distinct translation units and 96 KB of UTF-8 source.")
    for key in files:
        if (len(key) > 160 or not all(SEGMENT.fullmatch(part) for part in key.split("/"))
                or not key.endswith((".h", ".c"))):
            raise WorkerError("unsupported_configuration", "Use relative .c and .h paths with ordinary path components.")
        if any(key.startswith(other + "/") for other in files if other != key):
            raise WorkerError("unsupported_configuration", "A file cannot also be a parent directory.")
    if any(entry not in files or not entry.endswith(".c") for entry in entries):
        raise WorkerError("unsupported_configuration", "Each translation unit must name a submitted .c file.")
    if any("\x00" in source for source in files.values()):
        raise WorkerError("unsupported_configuration", "Source files cannot contain NUL bytes.")


def analyze(files, entries, standard):
    ready = capability()
    if ready.status != "available":
        return Analysis(status="unavailable", detail=ready.detail, standard=standard)
    if standard not in ready.standards:
        return Analysis(status="unsupported_configuration", detail="Choose c99, c11, c17 or c23.", standard=standard)
    if not SLOTS.acquire(blocking=False):
        return Analysis(status="request_limit", detail="Clang workers are busy. Retry shortly.", standard=standard)
    try:
        _validate(files, entries)
        with TemporaryDirectory(prefix="intentforge-c-") as name:
            home = Path(name)
            library = Path(os.environ["INTENTFORGE_LIBCLANG"]).resolve()
            (home / "request.json").write_text(json.dumps({"files": files, "entries": entries, "standard": standard}),
                                               encoding="utf-8")
            result = _run([str(library), "analyze"], home)
            return Analysis(version=ready.version, standard=standard, files=list(files), **result)
    except WorkerError as exc:
        return Analysis(status=exc.status, detail=exc.detail, standard=standard, version=ready.version)
    except (OSError, UnicodeError):
        return Analysis(status="unsupported_configuration", detail="Input or local staging is unavailable.",
                        standard=standard, version=ready.version)
    finally:
        SLOTS.release()
