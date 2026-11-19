"""Trusted in-process oracle. The HTTP application never instantiates it."""
import logging

from ai.behavior_oracle import BehaviorResult, ExecutionDetails, ExecutionLimits, Observation, RuntimeIssue, Status, Vector, program_identity
from analysis_evidence.source_map import SourceMap

from .interpreter import Execution, LIMITS, MAX_BYTES, Trace, interpret, prepare
from .runtime import INT_MAX, INT_MIN, RuntimeFault, WorkBudget

LOG = logging.getLogger(__name__)
MAX_VECTORS = 12
ORACLE_STEPS = 200_000


def compatible(value, type_name):
    if type_name == "bool":
        return type(value) is bool
    return type_name == "int" and type(value) is int and INT_MIN <= value <= INT_MAX


class MiniCOracle:
    def __init__(self, *, trace: bool = False, budget: WorkBudget | None = None):
        self.trace = trace
        self.budget = budget

    def verify(
        self, source: str, entry_point: str, vectors: tuple[Vector, ...], limits: ExecutionLimits,
        *, candidate_id: str | None = None,
    ) -> BehaviorResult:
        # Direct trusted callers must still pass contract-valid data.
        if len(source) > 96_000:
            raise ValueError("Source exceeds the trusted oracle's admission limit.")
        too_many = len(vectors) > MAX_VECTORS
        validated = tuple(Vector.model_validate(vector.model_dump()) for vector in vectors) if not too_many else ()
        return self._verify(source, entry_point, validated, limits, candidate_id, too_many=too_many)

    def _verify(self, source, entry_point, vectors, limits, candidate_id, *, too_many):
        digest = program_identity(source)
        identity = {"program": digest, "entry_point": entry_point, "candidate_id": candidate_id}
        if not vectors and not too_many:
            return BehaviorResult(**identity, status=Status.ORACLE_UNAVAILABLE, diagnostics=("No test vectors supplied.",))
        limits = ExecutionLimits.model_validate(limits.model_dump())
        mapper = SourceMap(source, "main.mc") if len(source) <= 24_000 and len(source.encode()) <= MAX_BYTES else None
        trace = Trace(mapper if self.trace else None)
        budget = self.budget if self.budget is not None else WorkBudget(ORACLE_STEPS)
        observations = []
        samples = []
        issue = None
        execution = None
        active_vector = None
        status = Status.BEHAVIOR_UNKNOWN
        try:
            if too_many:
                raise RuntimeFault("VERIFICATION_BUDGET", "At most twelve vectors are allowed.")
            program = prepare(source)
            entry = program.functions.get(entry_point)
            if entry is None:
                raise RuntimeFault("MISSING_ENTRY", "The selected Mini-C function does not exist.")
            if entry.return_type not in {"int", "bool"} or len(entry.parameters) > 16:
                raise RuntimeFault("UNSUPPORTED_ENTRY", "The entry must return int or bool and accept up to sixteen arguments.", entry)
            for index, vector in enumerate(vectors):
                if (len(vector.arguments) != len(entry.parameters)
                        or not all(compatible(argument, parameter.type_name)
                                   for argument, parameter in zip(vector.arguments, entry.parameters))
                        or not compatible(vector.expected, entry.return_type)):
                    active_vector = index
                    raise RuntimeFault("INVALID_VECTOR", "Test vector types, values or arity do not match the entry signature.", entry)
            for active_vector, vector in enumerate(vectors):
                execution = Execution(program, limits, budget, trace, active_vector)
                try:
                    value = interpret(execution.start(entry, vector.arguments))
                    if not compatible(value, entry.return_type):
                        raise RuntimeFault("INTERNAL_FAILURE", "The VM produced an invalid entry return value.", entry)
                    observations.append(Observation(vector=vector, actual=value))
                finally:
                    samples.append({"steps": execution.steps, "peak_cells": execution.peak_cells,
                                    "call_depth": execution.deepest_call})
            status = Status.MATCHES_SUPPLIED_TESTS if all(row.matches() for row in observations) else Status.MISMATCHES_SUPPLIED_TESTS
        except RuntimeFault as fault:
            limited = fault.code in LIMITS
            unsupported = fault.code in {"COMPILER_INVALID", "UNSUPPORTED_CONSTRUCT", "UNSUPPORTED_ENTRY", "MISSING_ENTRY", "INVALID_VECTOR"}
            status = Status.EXECUTION_LIMITED if limited else Status.EXECUTION_UNSUPPORTED if unsupported else Status.BEHAVIOR_UNKNOWN
            span = mapper.span(fault.node.span) if mapper and fault.node else None
            issue = RuntimeIssue(code=fault.code, message=fault.message, vector=active_vector, span=span)
            if execution:
                execution.event("EXECUTION_LIMIT" if limited else "RUNTIME_ERROR", fault.node)
        except Exception:
            # Keep implementation faults distinct from program failures and never expose source.
            LOG.error("Mini-C VM encountered an internal interpreter failure")
            issue = RuntimeIssue(code="INTERNAL_FAILURE", message="The Mini-C interpreter stopped unexpectedly.", vector=active_vector)
        return BehaviorResult(**identity, status=status, observations=tuple(observations),
                              diagnostics=(issue.message,) if issue else (),
                              unsupported=(issue.code,) if issue and status == Status.EXECUTION_UNSUPPORTED else (),
                              execution=ExecutionDetails(vectors=vectors, samples=tuple(samples), issue=issue,
                                                         trace=tuple(trace.events), trace_truncated=trace.truncated))
