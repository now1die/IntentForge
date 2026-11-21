"""One disposable Mini-C worker with no path, network or process syscalls."""
import ctypes as ct
import errno
import json
import os
import resource
import socket
import sys

from ai.behavior_oracle import Status, Vector
from ai.specification import includes_input
from vm.behavioral_executor import MiniCOracle, ORACLE_STEPS
from vm.interpreter import prepare
from vm.runtime import RuntimeFault, WorkBudget

from .contracts import Batch, BatchResult
from .probes import compare_probes, guided_inputs, ranked_probes

MAX_PRIVATE_INPUT = 384_000


def apply_filter():
    # Read/write uses inherited descriptors. No new file, socket or process
    # descriptors are available once the filter has been loaded.
    library = ct.CDLL("libseccomp.so.2")
    library.seccomp_init.argtypes = [ct.c_uint32]
    library.seccomp_init.restype = ct.c_void_p
    library.seccomp_syscall_resolve_name.argtypes = [ct.c_char_p]
    library.seccomp_rule_add.argtypes = [ct.c_void_p, ct.c_uint32, ct.c_int, ct.c_uint]
    library.seccomp_load.argtypes = [ct.c_void_p]
    library.seccomp_release.argtypes = [ct.c_void_p]
    rule = library.seccomp_init(0x00050000 | errno.EPERM)
    if not rule:
        raise OSError("Cannot allocate VM syscall policy")
    try:
        for syscall in (
            "read", "write", "writev", "close", "fstat", "lseek", "brk", "mmap",
            "munmap", "mremap", "mprotect", "madvise", "clock_gettime", "getrandom",
            "getpid", "gettid", "futex", "rt_sigaction", "rt_sigprocmask", "rt_sigreturn",
            "sigaltstack", "exit", "exit_group",
        ):
            number = library.seccomp_syscall_resolve_name(syscall.encode())
            if number < 0 or library.seccomp_rule_add(rule, 0x7FFF0000, number, 0):
                raise OSError("Cannot configure VM syscall policy")
        if library.seccomp_load(rule):
            raise OSError("Cannot activate VM syscall policy")
    finally:
        library.seccomp_release(rule)


def filter_witness():
    for operation in (lambda: os.open("/dev/null", os.O_RDONLY), socket.socket):
        try:
            descriptor = operation()
        except PermissionError:
            continue
        if type(descriptor) is int:
            os.close(descriptor)
        else:
            descriptor.close()
        raise OSError("The VM syscall deny check failed")


def run_batch(batch):
    shared = WorkBudget(ORACLE_STEPS)
    oracle = MiniCOracle(trace=batch.trace, budget=shared)
    vectors = tuple(Vector(arguments=row.arguments, expected=row.expected) for row in batch.vectors)
    runs = []
    eligible = []
    for program in batch.programs:
        result = oracle.verify(program.source, batch.entry_point, vectors, batch.limits,
                               candidate_id=program.candidate_id)
        runs.append(result)
        if program.candidate_id and result.status != Status.EXECUTION_UNSUPPORTED:
            try:
                eligible.append((program.candidate_id, prepare(program.source)))
            except RuntimeFault:
                continue
    arguments = tuple(row.arguments for row in vectors)
    if batch.engine_version in {7, 8}:
        def admitted_inputs(programs, entry, supplied):
            return tuple(row for row in guided_inputs(programs, entry, supplied)
                         if includes_input(batch.input_domain, row[0]))
        probes = ranked_probes(eligible, batch.entry_point, arguments, batch.limits, shared, input_strategy=admitted_inputs)
    else:
        probe_method = ranked_probes if batch.engine_version == 5 else compare_probes
        probes = probe_method(eligible, batch.entry_point, arguments, batch.limits, shared)
    return BatchResult(runs=tuple(runs), probes=probes)


def main():
    if sys.platform != "linux" or os.geteuid() == 0:
        raise SystemExit(4)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (2, 3))
    resource.setrlimit(resource.RLIMIT_AS, (192 * 1024**2, 192 * 1024**2))
    # Build trusted parser tables and preload codecs before denying filesystem access.
    sample = 'int probe(int x){return x+1;}'
    prepare(sample)
    "".encode("utf-16-le")
    apply_filter()
    filter_witness()
    if sys.argv[-1] == "probe":
        from ai.behavior_oracle import ExecutionLimits
        run = MiniCOracle().verify(sample, "probe", (Vector(arguments=(9,), expected=10),), ExecutionLimits())
        if run.status != Status.MATCHES_SUPPLIED_TESTS:
            raise SystemExit(4)
        print(json.dumps({"boundary": "isolated-local-v1"}))
        return
    raw = sys.stdin.buffer.read(MAX_PRIVATE_INPUT + 1)
    if len(raw) > MAX_PRIVATE_INPUT:
        raise SystemExit(4)
    print(run_batch(Batch.model_validate_json(raw)).model_dump_json())


if __name__ == "__main__":
    main()
