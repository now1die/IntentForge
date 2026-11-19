"""Generate small typed input sets. Probe execution has no expectation field."""
from itertools import combinations, zip_longest

from ai.intention_context import ast_children
from compiler import ast_nodes as ast
from vm.behavioral_executor import compatible
from vm.interpreter import Execution, LIMITS, Trace, interpret
from vm.runtime import INT_MAX, INT_MIN, RuntimeFault

from .contracts import Probe, ProbeResult, RankedProbe

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
        observations = observe(programs, entry, args, limits, budget)
        values = {(type(item.actual), item.actual) for item in observations if item.status == "observed"}
        relation = "disagree" if len(values) > 1 else (
            "agree" if all(item.status == "observed" for item in observations) else "inconclusive"
        )
        probes.append(Probe(arguments=args, relation=relation, candidates=tuple(observations)))
    return tuple(probes)


def observe(programs, entry, args, limits, budget):
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
    return tuple(observations)


def signed_literal(node):
    if isinstance(node, ast.Literal) and type(node.value) is int:
        return node.value
    if isinstance(node, ast.UnaryExpression) and node.operator == "-" and isinstance(node.operand, ast.Literal):
        if type(node.operand.value) is int:
            return -node.operand.value
    return None


def boundary_inputs(function, base):
    positions = {parameter.name: i for i, parameter in enumerate(function.parameters) if parameter.type_name == "int"}
    pending = [function.body]
    seen = []
    arrays = {}
    for _ in range(256):
        if not pending:
            break
        node = pending.pop()
        seen.append(node)
        if isinstance(node, ast.ArrayDeclaration):
            arrays.setdefault(node.name, []).append(signed_literal(node.size))
        pending.extend(child for _, child in ast_children(node))
    for node in seen:
        indexed = []
        if isinstance(node, ast.BinaryExpression) and node.operator in {"<", "<=", ">", ">=", "==", "!="}:
            indexed = [(node.left, signed_literal(node.right)), (node.right, signed_literal(node.left))]
        elif isinstance(node, ast.ArrayAccess) and isinstance(node.array, ast.Identifier):
            sizes = arrays.get(node.array.name, ())
            if len(sizes) == 1 and sizes[0] is not None:
                indexed = [(node.index, sizes[0])]
        for identifier, boundary in indexed:
            if not isinstance(identifier, ast.Identifier) or identifier.name not in positions or boundary is None:
                continue
            i = positions[identifier.name]
            for value in (boundary, boundary - 1, boundary + 1):
                if INT_MIN <= value <= INT_MAX:
                    yield (*base[:i], value, *base[i+1:])


def ranked_inputs(programs, entry, supplied):
    functions = [program.functions.get(entry) for program in programs]
    if any(function is None for function in functions) or any(program.program.globals for program in programs):
        return ()
    signature = tuple(p.type_name for p in functions[0].parameters)
    if (len(signature) > 4 or any(kind not in {"int", "bool"} for kind in signature)
            or any(tuple(p.type_name for p in function.parameters) != signature for function in functions)):
        return ()
    base = tuple(False if kind == "bool" else 0 for kind in signature)
    seen = {tuple((type(value), value) for value in inputs) for inputs in supplied}
    rows = []

    def add(args, basis):
        key = tuple((type(value), value) for value in args)
        if key not in seen:
            rows.append((args, basis))
            seen.add(key)

    for suggestions in zip_longest(*(boundary_inputs(function, base) for function in functions)):
        for args in suggestions:
            if args is not None:
                add(args, "boundary")
        if len(rows) >= 4:
            break
    del rows[4:]
    for pattern in ((1, 1), (-1, 1)):
        if len(base) > 1:
            add(tuple((True if kind == "bool" else pattern[i % 2]) for i, kind in enumerate(signature)), "combination")
    add(base, "scalar_seed")
    for magnitude in (1, -1, 2, INT_MIN, INT_MAX):
        for i, kind in enumerate(signature):
            add((*base[:i], True if kind == "bool" else magnitude, *base[i+1:]), "scalar_seed")
            if len(rows) >= MAX_PROBES:
                return tuple(rows[:MAX_PROBES])
    return tuple(rows[:MAX_PROBES])


def comparable_outcome(item):
    if item.status == "observed":
        return ("value", type(item.actual), item.actual)
    if item.status in {"runtime_failure", "execution_limited"} and item.issue != "VERIFICATION_BUDGET":
        return (item.status, item.issue)
    return None


def ranked_probes(programs, entry, supplied, limits, budget):
    if len(programs) < 2:
        return ()
    inputs = ranked_inputs([program for _, program in programs], entry, supplied)
    measured = []
    for args, basis in inputs:
        if budget.remaining == 0:
            break
        before = budget.remaining
        observations = observe(programs, entry, args, limits, budget)
        pairs = set()
        distinctions = set()
        for left, right in combinations(observations, 2):
            a, b = comparable_outcome(left), comparable_outcome(right)
            if a is not None and b is not None and a != b:
                pairs.add((left.candidate_id, right.candidate_id))
                distinctions.add("different_values" if a[0] == b[0] == "value" else
                                 "candidate_runtime_failure" if "runtime_failure" in {a[0], b[0]} else
                                 "candidate_execution_limit")
        assessment = next((name for name in ("different_values", "candidate_runtime_failure", "candidate_execution_limit")
                           if name in distinctions), "same_values" if all(row.status == "observed" for row in observations)
                          else "insufficient_observations")
        measured.append((args, basis, observations, pairs, assessment, before - budget.remaining))

    ordered = []
    covered = set()
    while measured:
        best = max(range(len(measured)), key=lambda i: (len(measured[i][3] - covered), len(measured[i][3]),
                   measured[i][1] == "boundary", -measured[i][5]))
        args, basis, observations, pairs, assessment, cost = measured.pop(best)
        ordered.append(RankedProbe(arguments=args, candidates=observations, separated_pairs=len(pairs),
                       new_pairs=len(pairs - covered), steps=cost, assessment=assessment, input_basis=basis,
                       relation="disagree" if pairs else "agree" if assessment == "same_values" else "inconclusive"))
        covered.update(pairs)
    return tuple(ordered)
