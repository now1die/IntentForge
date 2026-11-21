"""Bounded arithmetic constraints extracted from compiler-proven scalar slices.

This module projects a restricted CFG to mathematical terms. It has no Mini-C
runtime, native execution, or ability to evaluate arbitrary source.
"""
from dataclasses import dataclass
from time import monotonic

from compiler import ast_nodes as ast
from compiler.lexer import tokenize

from .intention_candidates import Edit, Evidence, Proposal
from .specification import INT_MAX, INT_MIN

COMPONENTS = frozenset({"arithmetic", "interprocedural"})
CATEGORIES = frozenset({"ARITHMETIC_COEFFICIENT", "ARITHMETIC_PREDECESSOR", "ARITHMETIC_OPERATOR_CONSTRAINT",
                        "ARITHMETIC_RETURN_DEPENDENCY"})
MAX_NODES = 160
MAX_DEPTH = 14
MAX_CALL_DEPTH = 2
MAX_TRIALS = 144
MAX_PROPOSALS = 4
OPERATOR_CLASS = {"+": ("-",), "-": ("+",), "*": ("/", "%"), "/": ("*", "%"), "%": ("*", "/")}


class UnsupportedProjection(ValueError):
    """The program slice does not fit the arithmetic model."""


class ProjectionLimit(ValueError):
    """The static arithmetic work budget was reached."""


@dataclass(frozen=True, slots=True)
class Term:
    operation: str
    children: tuple = ()
    value: int | None = None
    origin: int | None = None
    alternatives: tuple = ()


@dataclass(frozen=True, slots=True)
class Change:
    origin: int
    edit: Edit
    category: str
    action: str
    value: int | str


@dataclass(slots=True)
class Formula:
    output: Term
    obligations: tuple[Term, ...]
    changes: tuple[Change, ...]
    helpers: tuple[str, ...]


class Projector:
    def __init__(self, context, program, summaries, helper_shapes, enabled):
        self.context = context
        self.functions = {item.function.name: item for item in program.functions}
        self.bindings = program.bindings
        self.summaries = summaries
        self.helper_shapes = helper_shapes
        self.enabled = enabled
        self.deadline = program.deadline
        self.visits = 0
        self.obligations = []
        self.changes = {}
        self.helpers = set()

    def change(self, node, span, replacement, category, action, value):
        key = (id(node), span.start.offset, span.end.offset, replacement)
        self.changes[key] = Change(id(node), Edit(span, replacement), category, action, value)

    def expression(self, node, locals_, call_depth, depth=0, *, factor=False, returned=False):
        self.visits += 1
        if self.visits > MAX_NODES or depth > MAX_DEPTH or monotonic() >= self.deadline:
            raise ProjectionLimit
        origin = id(node)
        if isinstance(node, ast.Literal) and type(node.value) is int:
            if "arithmetic" in self.enabled and 0 <= node.value <= 128:
                for delta in (-1, 1, -2, 2):
                    nearby = node.value + delta
                    if nearby >= 0:
                        self.change(node, node.span, str(nearby), "ARITHMETIC_COEFFICIENT", "literal", nearby)
            return Term("literal", value=node.value, origin=origin)
        if isinstance(node, ast.Identifier):
            binding = self.bindings.identifiers.get(origin)
            if not binding or binding.id not in locals_:
                raise UnsupportedProjection
            alternatives = ()
            if factor and "arithmetic" in self.enabled:
                for sign, delta in (("-", -1), ("+", 1)):
                    self.change(node, node.span, f"({node.name} {sign} 1)", "ARITHMETIC_PREDECESSOR", "delta", delta)
            if returned and "interprocedural" in self.enabled:
                visible = self.context.visible_at(node.span.start.offset)
                alternatives = tuple((name, locals_[symbol.id]) for name, symbol in sorted(visible.items())
                                     if symbol.id in locals_ and symbol.id != binding.id and
                                     symbol.type.display() == "int" and symbol.id in self.locals_declared)
                for name, _ in alternatives:
                    self.change(node, node.span, name, "ARITHMETIC_RETURN_DEPENDENCY", "reference", name)
            return Term("identity", (locals_[binding.id],), origin=origin, alternatives=alternatives)
        if isinstance(node, ast.UnaryExpression) and node.operator in {"+", "-"}:
            if (node.operator == "-" and isinstance(node.operand, ast.Literal)
                    and type(node.operand.value) is int and node.operand.value == -INT_MIN):
                return Term("literal", value=INT_MIN)
            value = self.expression(node.operand, locals_, call_depth, depth + 1)
            return Term("negate" if node.operator == "-" else "identity", (value,))
        if isinstance(node, ast.BinaryExpression) and node.operator in OPERATOR_CLASS:
            if "arithmetic" in self.enabled:
                operator = next((token for token in self.context.parsed.tokens
                                 if node.left.span.end.offset <= token.span.start.offset < node.right.span.start.offset
                                 and token.lexeme == node.operator), None)
                if operator:
                    for alternate in OPERATOR_CLASS[node.operator]:
                        self.change(node, operator.span, alternate, "ARITHMETIC_OPERATOR_CONSTRAINT", "operation", alternate)
                if (node.operator in {"+", "-"} and isinstance(node.left, ast.Identifier)
                        and isinstance(node.right, ast.Literal) and node.right.value == 1):
                    self.change(node, node.span, node.left.name, "ARITHMETIC_PREDECESSOR", "drop_offset", 0)
            left = self.expression(node.left, locals_, call_depth, depth + 1, factor=node.operator == "*")
            right = self.expression(node.right, locals_, call_depth, depth + 1, factor=node.operator == "*")
            return Term(node.operator, (left, right), origin=origin)
        if (isinstance(node, ast.FunctionCall) and isinstance(node.callee, ast.Identifier)
                and "interprocedural" in self.enabled):
            name = node.callee.name
            if name not in self.helper_shapes or call_depth >= MAX_CALL_DEPTH:
                raise UnsupportedProjection
            arguments = tuple(self.expression(arg, locals_, call_depth, depth + 1) for arg in node.arguments)
            self.obligations.extend(arguments)
            self.helpers.add(name)
            return self.function(name, arguments, call_depth + 1)
        raise UnsupportedProjection

    def function(self, name, arguments, call_depth=0):
        item = self.functions.get(name)
        summary = self.summaries.get(name)
        if (item is None or summary is None or not summary["complete"] or summary["possible_global_reads"]
                or summary["possible_global_writes"] or item.function.return_type != "int"
                or any(param.type_name != "int" for param in item.function.parameters)):
            raise UnsupportedProjection
        graph = item.flow.graph
        locals_ = {self.bindings.declaration(param): arg
                   for param, arg in zip(item.function.parameters, arguments, strict=True)}
        outgoing = graph.outgoing()
        site = graph.entry
        for _ in range(24):
            edges = outgoing[site]
            if len(edges) != 1 or edges[0].kind != "next":
                raise UnsupportedProjection
            site = edges[0].target
            block = graph.blocks[site]
            if block.kind == "return":
                if block.expression is None:
                    raise UnsupportedProjection
                return self.expression(block.expression, locals_, call_depth, returned=True)
            node = block.syntax
            if not isinstance(node, ast.VariableDeclaration) or node.type_name != "int" or node.initializer is None:
                raise UnsupportedProjection
            value = self.expression(node.initializer, locals_, call_depth)
            binding = self.bindings.declaration(node)
            if binding is None:
                raise UnsupportedProjection
            self.locals_declared.add(binding)
            locals_[binding] = value
            self.obligations.append(value)
        raise ProjectionLimit

    def build(self, entry, arity):
        self.locals_declared = set()
        output = self.function(entry, tuple(Term("parameter", value=i) for i in range(arity)))
        return Formula(output, tuple(self.obligations), tuple(self.changes.values()), tuple(sorted(self.helpers)))


def signed(value):
    if not INT_MIN <= value <= INT_MAX:
        raise ArithmeticError("Outside checked integer range")
    return value


def quotient(a, b):
    if b == 0:
        raise ArithmeticError("Zero divisor")
    return (-1 if (a < 0) != (b < 0) else 1) * (abs(a) // abs(b))


def arithmetic_value(operation, a, b):
    if operation == "+":
        return signed(a + b)
    if operation == "-":
        return signed(a - b)
    if operation == "*":
        return signed(a * b)
    q = signed(quotient(a, b))
    return signed(q) if operation == "/" else signed(a - q * b)


def project(formula, inputs, change=None):
    """Substitute one input into the bounded arithmetic constraints."""
    values = {}

    def substitute(term):
        key = id(term)
        if key in values:
            return values[key]
        applied = change if change is not None and term.origin == change.origin else None
        if applied and applied.action == "reference":
            matching = dict(term.alternatives).get(applied.value)
            if matching is None:
                raise ArithmeticError("Unresolved alternate binding")
            value = substitute(matching)
        elif term.operation == "literal":
            value = signed(applied.value if applied else term.value)
        elif term.operation == "parameter":
            value = inputs[term.value]
        elif term.operation == "identity" or applied and applied.action == "drop_offset":
            value = substitute(term.children[0])
            if applied and applied.action == "delta":
                value = signed(value + applied.value)
        elif term.operation == "negate":
            value = signed(-substitute(term.children[0]))
        else:
            a, b = (substitute(child) for child in term.children)
            value = arithmetic_value(applied.value if applied else term.operation, a, b)
        values[key] = value
        return value

    try:
        for obligation in formula.obligations:
            substitute(obligation)
        return substitute(formula.output)
    except ArithmeticError:
        return None


def edit_cost(context, edit):
    original = [token.lexeme for token in tokenize(context.text(edit.span))[0]]
    replacement = [token.lexeme for token in tokenize(edit.replacement)[0]]
    # A stable prefix/suffix count makes a literal substitution cost one.
    while original and replacement and original[0] == replacement[0]:
        original.pop(0)
        replacement.pop(0)
    while original and replacement and original[-1] == replacement[-1]:
        original.pop()
        replacement.pop()
    return max(len(original), len(replacement))


def synthesize(context, program, summaries, helpers, specification, enabled):
    report = {"status": "INCOMPLETE_SPECIFICATION", "trials": 0, "compatible_edits": 0, "helper_functions": []}
    if not enabled:
        return (), report | {"status": "SPECIFICATION_ONLY"}
    examples = specification.examples
    if len({example.args for example in examples}) < 2:
        return (), report
    if specification.return_type != "int" or any(kind != "int" for _, kind in specification.parameters):
        return (), report | {"status": "UNSUPPORTED_EXPRESSION"}
    if program.status != "AVAILABLE":
        return (), report | {"status": program.status}
    projector = Projector(context, program, summaries, helpers, enabled)
    try:
        formula = projector.build(specification.function, len(specification.parameters))
    except ProjectionLimit:
        return (), report | {"status": "ANALYSIS_LIMITED"}
    except UnsupportedProjection:
        return (), report | {"status": "UNSUPPORTED_EXPRESSION"}
    report["helper_functions"] = list(formula.helpers)
    original = [project(formula, example.args) for example in examples]
    if any(value is None for value in original):
        return (), report | {"status": "UNSUPPORTED_CHECKED_ARITHMETIC"}
    expected = [example.expected_return for example in examples]
    if original == expected:
        return (), report | {"status": "CONSTRAINTS_ALREADY_AGREE"}
    proposed = []
    limited = False
    for index, change in enumerate(formula.changes):
        if monotonic() >= program.deadline or index >= MAX_TRIALS:
            limited = True
            break
        report["trials"] += 1
        if all(project(formula, example.args, change) == example.expected_return for example in examples):
            cost = edit_cost(context, change.edit)
            proposed.append((cost, change))
    proposed.sort(key=lambda row: (row[0], row[1].edit.span.start.offset, row[1].edit.replacement))
    report["compatible_edits"] = len(proposed)
    report["status"] = ("ANALYSIS_LIMITED" if limited else "MULTIPLE_COMPATIBLE_EDITS" if len(proposed) > 1
                        else "COMPATIBLE_EDIT" if proposed else "NO_COMPATIBLE_EDIT")
    report["minimum_changed_tokens"] = proposed[0][0] if proposed else None
    choices = []
    chosen = []
    # Preserve alternate locations when equally small edits fit the same examples.
    for cost, change in proposed:
        if monotonic() >= program.deadline or len(choices) == MAX_PROPOSALS:
            break
        if change.edit in chosen:
            continue
        chosen.append(change.edit)
        detail = f"A {cost}-token edit satisfies the bounded arithmetic constraints at {len(examples)} supplied inputs."
        choices.append(Proposal(
            (change.edit,), change.category, (Evidence("ARITHMETIC_CONSTRAINT_WITNESS", detail, change.edit.span),),
            "Review this arithmetic hypothesis with the isolated verifier.", "ScalarExpression", "value", type_match=True,
            counter_evidence=(Evidence("FINITE_DOMAIN", "Other edits may agree at the supplied inputs. Indexing and behavior elsewhere remain unspecified.",
                                       change.edit.span),),
        ))
    return tuple(choices), report
