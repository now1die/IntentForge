"""Generate small typed input sets. Probe execution has no expectation field."""
from ai.intention_context import ast_children
from compiler import ast_nodes as ast
from vm.behavioral_executor import compatible
from vm.interpreter import Execution, LIMITS, Trace, interpret
from vm.runtime import INT_MAX, INT_MIN, RuntimeFault

from .contracts import Probe, ProbeResult

MAX_PROBES = 8


def input_probes(programs, entry, supplied):
    functions = [program.functions[entry] for program in programs if entry in program.functions]
    if len(functions) != len(programs) or any(program.program.globals for program in programs):
        return ()
    signature = tuple(p.type_name for p in functions[0].parameters)
    if any(tuple(p.type_name for p in f.parameters) != signature for f in functions):
        return ()
    if len(signature) > 4 or any(kind not in {"int", "bool"} for kind in signature):
        return ()
    base = tuple(False if kind == "bool" else 0 for kind in signature)
    suggestions = [base]
    positions = {parameter.name: i for i, parameter in enumerate(functions[0].parameters)}
    stack = [functions[0].body]
    while stack and len(suggestions) < 4:
        node = stack.pop()
        condition = getattr(node, "condition", None)
        if (isinstance(condition, ast.BinaryExpression)
                and isinstance(condition.left, ast.Identifier) and isinstance(condition.right, ast.Literal)
                and type(condition.right.value) is int):
            i = positions.get(condition.left.name)
            if i is not None and signature[i] == "int":
                for value in range(condition.right.value - 1, condition.right.value + 2):
                    if INT_MIN <= value <= INT_MAX:
                        suggestions.append((*base[:i], value, *base[i+1:]))
        stack.extend(child for _, child in ast_children(node))
    for extreme in (1, -1, INT_MIN, INT_MAX, 2):
        for i, kind in enumerate(signature):
            value = True if kind == "bool" else extreme
            suggestions.append((*base[:i], value, *base[i+1:]))
    # The signature fixes types by position, making tuple membership type-safe.
    seen = set(supplied)
    chosen = []
    for inputs in suggestions:
        if inputs not in seen:
            chosen.append(inputs)
            seen.add(inputs)
            if len(chosen) == MAX_PROBES:
                break
    return tuple(chosen)


def compare_probes(programs, entry, supplied, limits, budget):
    if len(programs) < 2:
        return ()
    inputs = input_probes([row[1] for row in programs], entry, supplied)
    probes = []
    for args in inputs:
        if budget.remaining == 0:
            break
        observations = []
        for candidate_id, prepared in programs:
            function = prepared.functions[entry]
            execution = Execution(prepared, limits, budget, Trace(None), 0)
            try:
                value = interpret(execution.start(function, args))
                if not compatible(value, function.return_type):
                    raise RuntimeFault("UNSUPPORTED_ENTRY", "Probe requires a scalar return.")
            except RuntimeFault as fault:
                status = "execution_limited" if fault.code in LIMITS else (
                    "unsupported" if fault.code == "UNSUPPORTED_ENTRY" else "runtime_failure"
                )
                observations.append(ProbeResult(candidate_id=candidate_id, status=status, issue=fault.code))
            else:
                observations.append(ProbeResult(candidate_id=candidate_id, status="observed", actual=value))
        values = {(type(item.actual), item.actual) for item in observations if item.status == "observed"}
        relation = "disagree" if len(values) > 1 else (
            "agree" if all(item.status == "observed" for item in observations) else "inconclusive"
        )
        probes.append(Probe(arguments=args, relation=relation, candidates=tuple(observations)))
    return tuple(probes)
