"""Bounded finite constraints over compiler-selected CFG edges and typed scalar slots.

The projection admits a closed grammar. Indexed storage is represented by facts
for a small, fixed set of lexical cells. Missing facts and unsupported effects
stop the projection. Only the isolated service executes candidate programs.
"""
from collections import defaultdict
from dataclasses import dataclass
from time import monotonic

from analysis_evidence.dataflow import effects
from compiler import ast_nodes as ast
from compiler.source_location import SourceSpan

from .intention_phase8 import MAX_DEPTH, ProjectionLimit, Term, UnsupportedProjection, substitution
from .intention_phase85 import BOUNDARY_ALTERNATES, ScalarProjection
from .intention_phase9_loops import ORDER, step_expression

MAX_TERMS = 300
MAX_BLOCKS = 85
MAX_TRANSFERS = 650
MAX_LOOP_POINTS = 64
MAX_ARRAY_CELLS = 32
MAX_FUNCTIONS = 4
MAX_CALL_DEPTH = 2
WINDOW = "WINDOW_BOUNDARY_CONSTRAINT"
RANGE = "RANGE_ORIGIN_CONSTRAINT"
UPDATES = {"+=", "-=", "*=", "/=", "%="}


def contained(outer, inner):
    return outer.start.offset <= inner.start.offset and inner.end.offset <= outer.end.offset


class InvalidSample(ArithmeticError):
    """A required scalar or cell fact is missing or outside its extent."""


class Facts(dict):
    def __missing__(self, key):
        raise InvalidSample("The access has no initialized fact")


@dataclass(frozen=True, slots=True)
class Write:
    slot: int
    value: Term | None = None
    index: Term | None = None
    size: int = 0
    operation: str = "="
    origin: int | None = None


@dataclass(frozen=True, slots=True)
class Loop:
    slot: int
    direction: int
    squared: bool
    span: SourceSpan
    relation: str
    bound: str
    init: str
    latch: str
    indexed_bindings: tuple


@dataclass(slots=True)
class Function:
    entry: int
    args: tuple
    edges: list
    steps: dict
    loops: dict
    latches: dict


class FlowProjection(ScalarProjection):
    def __init__(self, context, program, components):
        super().__init__(context, program)
        # This phase synthesizes only the explicitly registered control edits.
        self.enabled = frozenset()
        self.components = components
        self.models = {}
        self.compiling = []
        self.layout = {}
        self.array_slots = {}
        self.expressions = 0

    def binding(self, node):
        if not isinstance(node, ast.Identifier):
            raise UnsupportedProjection
        symbol = self.bindings.identifiers.get(id(node))
        if symbol is None or symbol.id in self.bindings.globals:
            raise UnsupportedProjection
        return symbol.id

    def expression(self, node, locals_, call_depth, depth=0, **flags):
        self.expressions += 1
        if self.expressions > MAX_TERMS or depth > MAX_DEPTH or monotonic() >= self.deadline:
            raise ProjectionLimit
        if isinstance(node, ast.ArrayAccess):
            array = self.binding(node.array)
            if array not in self.array_slots:
                raise UnsupportedProjection
            index = self.expression(node.index, locals_, call_depth, depth+1)
            return Term("cell", (index,), value=self.array_slots[array], origin=id(node))
        if isinstance(node, ast.FunctionCall):
            if not isinstance(node.callee, ast.Identifier) or "helpers" not in self.components:
                raise UnsupportedProjection
            # Guard/latch dependency arguments are analyzed from an invariant
            # layout. Calls are excluded there to keep the proof local.
            if locals_ is not self.layout:
                raise UnsupportedProjection
            name = node.callee.name
            args = tuple(self.scalar(arg, depth+1) for arg in node.arguments)
            return self.call_term(node, name, args)
        if isinstance(node, ast.Literal) and type(node.value) is bool:
            return Term("literal", value=node.value)
        return super().expression(node, locals_, call_depth, depth, **flags)

    def call_term(self, node, name, args):
        self.compile(name)
        return Term("helper", args, value=name)

    def loop_site(self, item, block, initializations):
        node = block.syntax
        if not isinstance(node,ast.ForStatement) or id(node.initializer) not in initializations:
            raise UnsupportedProjection
        return self.loop(item,block,initializations[id(node.initializer)])

    def loop_sites(self, item):
        return [block for block in item.flow.graph.blocks if block.kind=="loop_header" and block.id in item.reachable]

    def latch_transfer(self, node):
        return self.assignment(node)

    def boolean(self, node, locals_, depth=0):
        if isinstance(node, (ast.Identifier, ast.FunctionCall)):
            return self.expression(node, locals_, 0, depth)
        return super().boolean(node, locals_, depth)

    def comparison_change(self, node):
        # Branch tests are structural guards, never synthesized by borrowing
        # the Phase 8.5 comparison alternatives.
        return None

    def change(self, node, span, replacement, category, action, value):
        if category in {WINDOW, RANGE}:
            super().change(node, span, replacement, category, action, value)

    def scalar(self, node, depth=0):
        kind = self.context.semantic.expression_types.get(id(node))
        if kind is None or kind.display() not in {"bool","int"}:
            raise UnsupportedProjection
        if kind.display() == "bool":
            return self.boolean(node, self.layout, depth)
        return self.expression(node, self.layout, 0, depth)

    def declaration(self, node):
        binding = self.bindings.declaration(node)
        if isinstance(node, ast.ArrayDeclaration):
            if binding not in self.array_slots:
                raise UnsupportedProjection
            return Write(self.array_slots[binding], size=node.size.value)
        if binding not in self.layout:
            raise UnsupportedProjection
        return Write(self.layout[binding].value, self.scalar(node.initializer) if node.initializer is not None else None)

    def assignment(self, node):
        if isinstance(node, ast.ExpressionStatement):
            node = node.expression
        if isinstance(node, ast.Assignment) and node.operator in {"=", *UPDATES}:
            operand, value, operator = node.target, self.scalar(node.value), node.operator
        elif isinstance(node, ast.UpdateExpression):
            operand, value = node.operand, Term("literal", value=1)
            operator = "+=" if node.operator == "++" else "-="
        else:
            raise UnsupportedProjection
        if isinstance(operand, ast.ArrayAccess):
            array = self.binding(operand.array)
            if array not in self.array_slots:
                raise UnsupportedProjection
            return Write(self.array_slots[array], value, self.scalar(operand.index), operation=operator, origin=id(operand))
        binding = self.binding(operand)
        if binding not in self.layout:
            raise UnsupportedProjection
        return Write(self.layout[binding].value, value, operation=operator)

    def shifted_bound(self, guard, limit, increasing):
        token = self.operator_span(guard)
        if token is None:
            raise UnsupportedProjection
        super().change(guard, token, BOUNDARY_ALTERNATES[guard.operator], WINDOW, "operation",
                       BOUNDARY_ALTERNATES[guard.operator])
        if not (isinstance(limit, ast.BinaryExpression) and limit.operator in {"+","-"}
                and isinstance(limit.right, ast.Literal) and type(limit.right.value) is int):
            return
        # Only the one-integer shift equivalent to toggling strictness is
        # admitted here. The checked bound term is re-evaluated per sample.
        delta = (1 if guard.operator in {"<",">"} else -1)*(1 if increasing else -1)
        new = limit.right.value + delta*(1 if limit.operator=="+" else -1)
        if new >= 0 and not (limit.operator=="-" and limit.right.value==0):
            super().change(limit.right, limit.right.span, str(new), WINDOW, "literal", new)

    def loop(self, item, block, init_site):
        node, graph = block.syntax, item.flow.graph
        initial = node.initializer
        if not isinstance(initial, ast.VariableDeclaration) or initial.type_name != "int" or initial.initializer is None:
            raise UnsupportedProjection
        binding = self.bindings.declaration(initial)
        if binding not in self.layout:
            raise UnsupportedProjection
        guard = node.condition
        if not isinstance(guard, ast.BinaryExpression) or guard.operator not in ORDER:
            raise UnsupportedProjection

        def induction(expression):
            if self.identifier(expression)==binding:
                return "direct"
            if (isinstance(expression,ast.BinaryExpression) and expression.operator=="*"
                    and self.identifier(expression.left)==self.identifier(expression.right)==binding):
                return "square"
            return None

        shape = induction(guard.left)
        reverse = shape is None
        shape = induction(guard.right) if reverse else shape
        if shape is None:
            raise UnsupportedProjection
        limit = guard.left if reverse else guard.right
        relation = ORDER[guard.operator] if reverse else guard.operator
        direction = 1 if relation in {"<","<="} else -1
        if shape=="square" and direction<0:
            raise UnsupportedProjection
        body_blocks = [part for part in graph.blocks if contained(node.body.span, part.syntax.span)]
        writes = set().union(*(effects(part.expression or part.syntax,self.bindings,conservative_calls=False).writes
                               for part in body_blocks))
        if binding in writes:
            raise UnsupportedProjection
        invariant = {name:term for name,term in self.layout.items() if name not in writes and name != binding}
        # Bounds are scalar terms in invariant lexical bindings. Indexed reads
        # would depend on mutable storage and are excluded from the proof.
        if any(isinstance(record.node,(ast.ArrayAccess,ast.FunctionCall)) and
               contained(limit.span,record.node.span) for record in self.context.nodes):
            raise UnsupportedProjection
        self.expression(limit,invariant,0)
        if node.update is None:
            raise UnsupportedProjection
        step_expression(self,binding,node.update,invariant)
        if any(isinstance(record.node,(ast.ArrayAccess,ast.FunctionCall)) and
               contained(node.update.span,record.node.span) for record in self.context.nodes):
            raise UnsupportedProjection

        if "windows" in self.components:
            self.shifted_bound(guard,limit,direction>0)
        if ("range" in self.components and isinstance(initial.initializer,ast.Literal)
                and type(initial.initializer.value) is int and shape=="direct"):
            visible = self.context.visible_at(initial.initializer.span.start.offset)
            reaching = item.flow.incoming[init_site]
            defined = {row.binding for row in reaching} - {
                row.binding for row in reaching if
                (row.site==graph.entry and self.bindings.symbols[row.binding].kind.value!="parameter")
                or (isinstance(graph.blocks[row.site].syntax,ast.VariableDeclaration)
                    and graph.blocks[row.site].syntax.initializer is None)
            }
            for name, symbol in list(sorted(visible.items(),key=lambda pair:pair[1].declaration_span.start.offset))[-4:]:
                if symbol.id in invariant and symbol.id in defined and symbol.type.display()=="int":
                    super().change(initial.initializer,initial.initializer.span,name,RANGE,"reference",name)
        indexed = tuple(sorted({record.node.array.name for record in self.context.nodes
                                if isinstance(record.node,ast.ArrayAccess) and isinstance(record.node.array,ast.Identifier)
                                and contained(node.body.span,record.node.span)}))
        return Loop(self.layout[binding].value,direction,shape=="square",guard.span,relation,
                    self.context.text(limit.span),self.context.text(initial.initializer.span),
                    self.context.text(node.update.span),indexed)

    def compile(self,name):
        if name in self.compiling:
            raise UnsupportedProjection
        if name in self.models:
            return self.models[name]
        if len(self.compiling)>MAX_CALL_DEPTH or len(self.models)+len(self.compiling)>=MAX_FUNCTIONS:
            raise ProjectionLimit
        item = self.functions.get(name)
        if not item or not item.flow.complete or item.function.return_type not in {"int","bool"}:
            raise UnsupportedProjection
        graph = item.flow.graph
        if len(item.reachable)>MAX_BLOCKS:
            raise ProjectionLimit
        declarations = dict.fromkeys(self.bindings.declaration(node) for node in item.function.parameters)
        arrays = {}
        for block in graph.blocks:
            node = block.syntax
            if isinstance(node,ast.VariableDeclaration):
                declarations[self.bindings.declaration(node)] = None
            elif isinstance(node,ast.ArrayDeclaration):
                if (node.type_name!="int" or not isinstance(node.size,ast.Literal) or type(node.size.value) is not int
                        or not 1<=node.size.value<=MAX_ARRAY_CELLS):
                    raise UnsupportedProjection
                arrays[self.bindings.declaration(node)] = node.size.value
        if (None in declarations or None in arrays or sum(arrays.values())>MAX_ARRAY_CELLS
                or any(self.bindings.symbols[key].type.display() not in {"int","bool"} for key in declarations)):
            raise UnsupportedProjection
        old_layout, old_arrays = self.layout, self.array_slots
        self.layout = {key:Term("parameter",value=i) for i,key in enumerate(declarations)}
        self.array_slots = {key:len(declarations)+i for i,key in enumerate(arrays)}
        self.compiling.append(name)
        try:
            edges = graph.outgoing()
            loops, latches, steps = {}, {}, {}
            initializations = {id(block.syntax):block.id for block in graph.blocks if block.kind=="statement"}
            for block in self.loop_sites(item):
                loops[block.id] = self.loop_site(item,block,initializations)
            if len(loops)>3:
                raise ProjectionLimit
            for block in graph.blocks:
                if block.id not in item.reachable:
                    continue
                kind, node = block.kind, block.syntax
                if kind in {"return","branch","loop_header"}:
                    transition = self.scalar(block.expression)
                elif kind=="statement" and isinstance(node,(ast.VariableDeclaration,ast.ArrayDeclaration)):
                    transition = self.declaration(node)
                    if isinstance(node,ast.VariableDeclaration) and isinstance(node.initializer,ast.Literal):
                        alternatives = tuple((change.value,self.layout[
                            self.context.visible_at(node.initializer.span.start.offset)[change.value].id])
                            for change in self.changes.values()
                            if change.category==RANGE and change.origin==id(node.initializer))
                        if alternatives:
                            transition = Write(transition.slot, Term("identity",(transition.value,),
                                               origin=id(node.initializer),alternatives=alternatives))
                elif kind in {"statement","loop_latch"}:
                    if kind=="loop_latch":
                        header = edges[block.id][0].target
                        transition = self.latch_transfer(node)
                        latches[block.id] = (header, loops[header])
                    else:
                        transition = self.assignment(node)
                elif kind in {"entry","exit","break","continue"}:
                    transition = None
                else:
                    raise UnsupportedProjection
                steps[block.id] = (kind,transition)
            function = Function(graph.entry, tuple(self.layout[self.bindings.declaration(node)].value
                                for node in item.function.parameters), edges, steps, loops, latches)
            self.models[name] = function
            return function
        finally:
            self.compiling.pop()
            self.layout, self.array_slots = old_layout, old_arrays


@dataclass(slots=True)
class Sample:
    value: int | bool | None
    loops: dict
    exits: dict
    helpers: dict
    issue: str | None = None


def project(model,name,args,changes=(),*,trace=False,observer=None):
    remaining = MAX_TRANSFERS
    visits, exits, helpers = defaultdict(list), defaultdict(int), defaultdict(int)

    def function(label,values,depth,parent=None):
        nonlocal remaining
        if depth>(observer.depth_limit if observer is not None else MAX_CALL_DEPTH):
            raise ProjectionLimit
        if observer is not None:
            override = observer.enter(label, values, parent)
            if override is not None:
                return override
        item = model.models[label]
        facts = Facts(zip(item.args,values,strict=True))
        sizes, iterations, measures = {}, defaultdict(int), {}
        site = item.entry

        def cell(slot,index,origin=None,mode="read"):
            length = sizes.get(slot,0)
            if observer is not None:
                observer.cell(label, origin, index, length, (slot,index) in facts, mode)
            if type(index) is not int or not 0<=index<length:
                raise InvalidSample("INDEX_OUTSIDE_EXTENT")
            return (slot,index)

        def resolve(term,evaluate):
            if term.operation=="cell":
                return facts[cell(term.value,evaluate(term.children[0]),term.origin)]
            args = tuple(evaluate(child) for child in term.children)
            if trace:
                helpers[term.value] += 1
            return function(term.value,args,depth+1,(label,values))

        while True:
            remaining -= 1
            if remaining<0 or monotonic()>=model.deadline:
                raise ProjectionLimit
            kind, action = item.steps[site]
            edges = item.edges[site]
            evaluate = substitution(facts,changes,resolve=resolve)
            if kind=="return":
                if trace:
                    exits[f"{label}:return:{site}"] += 1
                return evaluate(action)
            if kind in {"branch","loop_header"}:
                edge_kind = "true" if evaluate(action) else "false"
                if kind=="loop_header":
                    summary = item.loops[site]
                    index = facts[summary.slot]
                    if getattr(summary,"squared",False) and index<0:
                        raise InvalidSample("NON_MONOTONE_SQUARE")
                    if edge_kind=="true":
                        if observer is not None:
                            measures[site] = observer.measure(summary, facts)
                        iterations[site] += 1
                        if iterations[site]>MAX_LOOP_POINTS:
                            raise ProjectionLimit
                        if trace:
                            visits[(label,site)].append(index)
                    elif trace:
                        exits[f"{label}:guard_false:{site}"] += 1
                branch = next((edge for edge in edges if edge.kind==edge_kind),None)
                if branch is None:
                    raise InvalidSample("UNMODELED_EDGE")
                site = branch.target
                continue
            if isinstance(action,Write):
                if action.size:
                    sizes[action.slot] = action.size
                    for index in range(action.size):
                        facts.pop((action.slot,index),None)
                elif action.value is None:
                    facts.pop(action.slot,None)
                else:
                    key = cell(action.slot,evaluate(action.index),action.origin,"write") if action.index else action.slot
                    operand = action.value
                    if action.operation!="=":
                        operand = Term(action.operation[:-1],(Term("literal",value=facts[key]),operand))
                    old = facts.get(key)
                    value = evaluate(operand)
                    if kind=="loop_latch" and (value-old)*item.latches[site][1].direction<=0:
                        raise InvalidSample("NON_PROGRESSING_LATCH")
                    facts[key] = value
            if kind=="loop_latch" and observer is not None and action is None:
                header, summary = item.latches[site]
                observer.progress(summary, facts, measures[header])
            if not edges:
                raise InvalidSample("NO_PROJECTED_RETURN")
            if trace and kind in {"break","continue"}:
                exits[f"{label}:{kind}:{site}"] += 1
            site = edges[0].target

    try:
        value = function(name,args,0)
    except ArithmeticError as exc:
        return Sample(None,visits,exits,helpers,str(exc) if isinstance(exc,InvalidSample) else "CHECKED_ARITHMETIC")
    return Sample(value,visits,exits,helpers)
