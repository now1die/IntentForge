"""Evaluate the validated Mini-C AST on an explicit continuation stack."""
from dataclasses import dataclass

from ai.behavior_oracle import ExecutionLimits, TraceEvent
from ai.intention_context import ContextLimit, build_context
from analysis_evidence.source_map import SourceMap
from compiler import ast_nodes as ast

from .arithmetic import binary
from .runtime import Environment, INT_MIN, RuntimeFault, UNINITIALIZED, WorkBudget, checked, load, truth

MAX_BYTES = 48_000
TRACE_ENTRIES = 64
TRACE_BYTES = 8_192
SUPPORTED = frozenset({
    ast.Program, ast.FunctionDefinition, ast.Parameter, ast.Block, ast.VariableDeclaration,
    ast.ArrayDeclaration, ast.ExpressionStatement, ast.Assignment, ast.IfStatement, ast.WhileStatement,
    ast.ForStatement, ast.BreakStatement, ast.ContinueStatement, ast.ReturnStatement, ast.BinaryExpression,
    ast.UnaryExpression, ast.UpdateExpression, ast.Identifier, ast.Literal, ast.FunctionCall, ast.ArrayAccess,
})
LIMITS = {"STEP_LIMIT", "CALL_DEPTH", "MEMORY_CELLS", "VERIFICATION_BUDGET", "SOURCE_LIMIT"}


@dataclass(frozen=True)
class Prepared:
    program: ast.Program
    functions: dict[str, ast.FunctionDefinition]


def prepare(source: str) -> Prepared:
    if len(source) > 24_000 or len(source.encode()) > MAX_BYTES:
        raise RuntimeFault("SOURCE_LIMIT", "Mini-C source exceeds the VM input limit.")
    try:
        context = build_context(source)
    except (ContextLimit, RecursionError) as exc:
        raise RuntimeFault("SOURCE_LIMIT", "Mini-C source exceeds the compiler complexity limit.") from exc
    except TypeError as exc:
        # The existing parser produces a declaration list for a bare control
        # body and rejects it while building the enclosing source span.
        if str(exc) != "Cannot obtain source span for list":
            raise
        raise RuntimeFault("UNSUPPORTED_CONSTRUCT", "Wrap control-body declarations in a block.") from exc
    if not context.compiler_valid or context.parsed.ast is None:
        raise RuntimeFault("COMPILER_INVALID", "Execution requires compiler-valid Mini-C.")
    for record in context.nodes:
        node = record.node
        if type(node) not in SUPPORTED:
            raise RuntimeFault("UNSUPPORTED_CONSTRUCT", "This AST construct is outside the VM subset.", node)
        kind = getattr(node, "literal_type", None) or getattr(node, "type_name", None) or getattr(node, "return_type", None)
        if kind and kind not in {"int", "bool", "void"}:
            raise RuntimeFault("UNSUPPORTED_CONSTRUCT", f"The VM does not execute {kind} values.", node)
        if isinstance(node, ast.FunctionCall) and not isinstance(node.callee, ast.Identifier):
            raise RuntimeFault("UNSUPPORTED_CONSTRUCT", "Only direct Mini-C function calls are supported.", node)
        arms = (node.then_branch, node.else_branch) if isinstance(node, ast.IfStatement) else (
            (node.body,) if isinstance(node, (ast.WhileStatement, ast.ForStatement)) else ()
        )
        if any(isinstance(arm, (ast.VariableDeclaration, ast.ArrayDeclaration)) for arm in arms):
            raise RuntimeFault("UNSUPPORTED_CONSTRUCT", "Wrap control-body declarations in a block.", node)
    program = context.parsed.ast
    return Prepared(program, {function.name: function for function in program.functions})


class Trace:
    """One bounded record of events across all vectors in an oracle invocation."""

    def __init__(self, mapper: SourceMap | None):
        self.mapper = mapper
        self.events: list[TraceEvent] = []
        self.remaining = TRACE_BYTES
        self.truncated = False

    def add(self, event, node, vector, step):
        if self.mapper is None or self.truncated:
            return
        if len(self.events) >= TRACE_ENTRIES:
            self.truncated = True
            return
        span = self.mapper.span(node.span) if node else None
        record = TraceEvent(kind=event, vector=vector, step=step, span=span)
        # Include a conservative allowance for the enclosing array separators.
        size = len(record.model_dump_json().encode()) + 2
        if self.remaining < size:
            self.truncated = True
            return
        self.remaining -= size
        self.events.append(record)


@dataclass(frozen=True)
class Flow:
    kind: str
    value: int | bool | None = None


def interpret(root):
    """Run child generators without using Python's recursive call stack."""
    tasks = [root]
    value = None
    try:
        while tasks:
            try:
                child = tasks[-1].send(value)
            except StopIteration as done:
                tasks.pop()
                value = done.value
            else:
                tasks.append(child)
                value = None
        return value
    finally:
        for task in reversed(tasks):
            task.close()


class Execution:
    def __init__(self, program: Prepared, limits: ExecutionLimits, budget: WorkBudget, trace: Trace, vector: int):
        self.program = program
        self.limits = limits
        self.budget = budget
        self.trace = trace
        self.vector = vector
        self.globals = Environment()
        self.frames: list[str] = []
        self.steps = 0
        self.live_cells = 0
        self.peak_cells = 0
        self.deepest_call = 0

    def step(self, node, count=1):
        if self.steps + count > self.limits.steps:
            raise RuntimeFault("STEP_LIMIT", "Per-vector execution step limit reached.", node)
        self.budget.consume(node, count)
        self.steps += count

    def event(self, kind, node):
        self.trace.add(kind, node, self.vector, self.steps)

    def allocate(self, scope, count, node):
        if self.live_cells + count > self.limits.memory_cells:
            raise RuntimeFault("MEMORY_CELLS", "Live variable and array cell limit reached.", node)
        scope.cells += count
        self.live_cells += count
        self.peak_cells = max(self.peak_cells, self.live_cells)

    def release(self, scope):
        self.live_cells -= scope.cells

    def start(self, entry, arguments):
        declarations = self.program.program.globals
        for declaration in declarations:
            self.step(declaration)
            self.allocate(self.globals, 1, declaration)
            if isinstance(declaration, ast.ArrayDeclaration):
                self.globals.values[declaration.name] = UNINITIALIZED
            else:
                self.globals.values[declaration.name] = False if declaration.type_name == "bool" else 0
        for declaration in declarations:
            yield self.declare(declaration, self.globals, registered=True)
        return (yield self.call(entry, arguments, entry))

    def declare(self, node, scope, *, registered=False):
        if not registered:
            self.allocate(scope, 1, node)
            scope.values[node.name] = UNINITIALIZED
        if isinstance(node, ast.ArrayDeclaration):
            length = yield self.expression(node.size, scope)
            if type(length) is not int or length <= 0:
                raise RuntimeFault("INVALID_ARRAY_SIZE", "Array length must be a positive integer.", node.size)
            self.allocate(scope, length, node)
            self.step(node, length)
            initial = (False if node.type_name == "bool" else 0) if registered else UNINITIALIZED
            scope.values[node.name] = [initial] * length
        elif node.initializer is not None:
            scope.values[node.name] = yield self.expression(node.initializer, scope)
        self.event("DECLARATION", node)

    def call(self, function, arguments, site):
        self.step(site)
        if len(self.frames) >= self.limits.call_depth:
            raise RuntimeFault("CALL_DEPTH", "Mini-C call-depth limit reached.", site)
        self.frames.append(function.name)
        self.deepest_call = max(self.deepest_call, len(self.frames))
        scope = Environment(self.globals)
        try:
            for parameter, actual in zip(function.parameters, arguments, strict=True):
                self.step(parameter)
                self.allocate(scope, 1, parameter)
                scope.values[parameter.name] = actual
            self.event("FUNCTION_ENTER", function)
            flow = yield self.statement(function.body, scope, share_scope=True)
            if flow is None and function.return_type != "void":
                raise RuntimeFault("MISSING_RETURN", "A non-void function reached the end without returning.", function)
            self.event("FUNCTION_RETURN", function)
            return flow.value if flow is not None else None
        finally:
            self.release(scope)
            self.frames.pop()

    def statement(self, node, scope, *, share_scope=False):
        self.step(node)
        if isinstance(node, ast.Block):
            local = scope if share_scope else Environment(scope)
            try:
                for statement in node.statements:
                    flow = yield self.statement(statement, local)
                    if flow is not None:
                        return flow
            finally:
                if not share_scope:
                    self.release(local)
        elif isinstance(node, (ast.VariableDeclaration, ast.ArrayDeclaration)):
            yield self.declare(node, scope)
        elif isinstance(node, ast.ExpressionStatement):
            if node.expression is not None:
                yield self.expression(node.expression, scope)
        elif isinstance(node, ast.IfStatement):
            value = yield self.expression(node.condition, scope)
            self.event("CONDITION_TRUE" if truth(value, node.condition) else "CONDITION_FALSE", node.condition)
            branch = node.then_branch if value else node.else_branch
            if branch is not None:
                return (yield self.statement(branch, scope))
        elif isinstance(node, (ast.WhileStatement, ast.ForStatement)):
            return (yield self.loop(node, scope))
        elif isinstance(node, ast.BreakStatement):
            return Flow("break")
        elif isinstance(node, ast.ContinueStatement):
            return Flow("continue")
        elif isinstance(node, ast.ReturnStatement):
            value = (yield self.expression(node.value, scope)) if node.value is not None else None
            return Flow("return", value)
        else:
            raise RuntimeFault("UNSUPPORTED_CONSTRUCT", "Unsupported statement.", node)
        return None

    def loop(self, node, parent):
        is_for = isinstance(node, ast.ForStatement)
        scope = Environment(parent) if is_for else parent
        try:
            if is_for and node.initializer is not None:
                init = node.initializer
                if isinstance(init, (ast.VariableDeclaration, ast.ArrayDeclaration)):
                    yield self.statement(init, scope)
                else:
                    yield self.expression(init, scope)
            while True:
                if node.condition is not None:
                    value = yield self.expression(node.condition, scope)
                    self.event("CONDITION_TRUE" if truth(value, node.condition) else "CONDITION_FALSE", node.condition)
                    if not value:
                        return None
                self.step(node)
                self.event("LOOP_ITERATION", node)
                flow = yield self.statement(node.body, scope)
                if flow is not None:
                    if flow.kind == "return":
                        return flow
                    if flow.kind == "break":
                        return None
                if is_for and node.update is not None:
                    yield self.expression(node.update, scope)
        finally:
            if is_for:
                self.release(scope)

    def location(self, node, scope):
        self.step(node)
        if isinstance(node, ast.Identifier):
            return scope.locate(node.name, node)
        if isinstance(node, ast.ArrayAccess) and isinstance(node.array, ast.Identifier):
            array = load(scope.locate(node.array.name, node.array), node.array)
            index = yield self.expression(node.index, scope)
            if not isinstance(array, list) or type(index) is not int:
                raise RuntimeFault("INVALID_OPERATION", "An array and integer index are required.", node)
            if index < 0 or index >= len(array):
                raise RuntimeFault("ARRAY_BOUNDS", "Array index is outside its declared length.", node.index)
            return array, index
        raise RuntimeFault("INVALID_OPERATION", "Expression is not an assignable location.", node)

    def expression(self, node, scope):
        self.step(node)
        if isinstance(node, ast.Literal):
            return checked(node.value, node) if node.literal_type == "int" else node.value
        if isinstance(node, ast.Identifier):
            return load(scope.locate(node.name, node), node)
        if isinstance(node, ast.ArrayAccess):
            return load((yield self.location(node, scope)), node)
        if isinstance(node, ast.BinaryExpression):
            left = yield self.expression(node.left, scope)
            if node.operator == "&&" and not truth(left, node.left):
                return False
            if node.operator == "||" and truth(left, node.left):
                return True
            right = yield self.expression(node.right, scope)
            return truth(right, node.right) if node.operator in {"&&", "||"} else binary(node.operator, left, right, node)
        if isinstance(node, ast.UnaryExpression):
            if node.operator == "-" and isinstance(node.operand, ast.Literal) and node.operand.value == -INT_MIN:
                self.step(node.operand)
                return INT_MIN
            operand = yield self.expression(node.operand, scope)
            if node.operator == "!":
                return not truth(operand, node)
            return checked(-operand if node.operator == "-" else operand, node)
        if isinstance(node, (ast.Assignment, ast.UpdateExpression)):
            target = node.target if isinstance(node, ast.Assignment) else node.operand
            location = yield self.location(target, scope)
            if isinstance(node, ast.Assignment):
                old = load(location, target) if node.operator != "=" else None
                value = yield self.expression(node.value, scope)
                if node.operator != "=":
                    value = binary(node.operator[:-1], old, value, node)
            else:
                old = load(location, target)
                value = checked(old + (1 if node.operator == "++" else -1), node)
            storage, key = location
            storage[key] = value
            self.event("ARRAY_UPDATED" if isinstance(storage, list) else "ASSIGNED", node)
            return old if isinstance(node, ast.UpdateExpression) and not node.prefix else value
        if isinstance(node, ast.FunctionCall):
            arguments = []
            for argument in node.arguments:
                arguments.append((yield self.expression(argument, scope)))
            return (yield self.call(self.program.functions[node.callee.name], arguments, node))
        raise RuntimeFault("UNSUPPORTED_CONSTRUCT", "Unsupported expression.", node)
