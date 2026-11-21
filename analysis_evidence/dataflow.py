"""Conservative statement-level reaching definitions and return slices."""
from collections import defaultdict, deque
from dataclasses import dataclass
from time import monotonic

from ai.intention_context import ast_children
from compiler import ast_nodes as ast
from compiler.symbol_table import SymbolKind

from .control_flow import Graph

MAX_TRANSFERS = 1_800
MAX_SLICE = 64


@dataclass(frozen=True, slots=True)
class Effects:
    reads: frozenset[str] = frozenset()
    writes: frozenset[str] = frozenset()
    definite: frozenset[str] = frozenset()
    calls: frozenset[str] = frozenset()
    array_access: bool = False


@dataclass(slots=True)
class BindingIndex:
    identifiers: dict
    declarations: dict
    symbols: dict
    globals: frozenset

    @classmethod
    def from_context(cls, context):
        symbols = {symbol.id: symbol for scope in context.scopes for symbol in scope.symbols.values()}
        declarations = {(symbol.name, symbol.declaration_span): symbol.id for symbol in symbols.values()}
        identifiers = {}
        for record in context.nodes:
            if isinstance(record.node, ast.Identifier):
                symbol = context.visible_at(record.node.span.start.offset).get(record.node.name)
                if symbol:
                    identifiers[id(record.node)] = symbol
        globals_ = frozenset(symbol.id for symbol in context.scopes[0].symbols.values()
                             if symbol.kind != SymbolKind.FUNCTION)
        return cls(identifiers, declarations, symbols, globals_)

    def declaration(self, node):
        return self.declarations.get((node.name, node.span))


def effects(expression, bindings, *, conservative_calls=True):
    if expression is None:
        return Effects()
    reads, writes, definite, calls = set(), set(), set(), set()
    array_access = False
    root = expression.expression if isinstance(expression, ast.ExpressionStatement) else expression
    if root is None:
        return Effects()
    pending = [root]
    while pending:
        node = pending.pop()
        if isinstance(node, ast.Identifier):
            symbol = bindings.identifiers.get(id(node))
            if symbol and symbol.kind != SymbolKind.FUNCTION:
                reads.add(symbol.id)
            continue
        if isinstance(node, (ast.VariableDeclaration, ast.ArrayDeclaration)):
            declared = bindings.declaration(node)
            if declared:
                writes.add(declared)
                if isinstance(node, ast.VariableDeclaration) and node is root:
                    definite.add(declared)
        if isinstance(node, (ast.Assignment, ast.UpdateExpression)):
            operand = node.target if isinstance(node, ast.Assignment) else node.operand
            identifier = operand.array if isinstance(operand, ast.ArrayAccess) else operand
            symbol = bindings.identifiers.get(id(identifier))
            if symbol:
                writes.add(symbol.id)
                if node is root and isinstance(operand, ast.Identifier):
                    definite.add(symbol.id)
            if isinstance(node, ast.Assignment) and node.operator == "=" and isinstance(operand, ast.Identifier):
                pending.append(node.value)
                continue
        if isinstance(node, ast.ArrayAccess):
            array_access = True
        if isinstance(node, ast.FunctionCall):
            if isinstance(node.callee, ast.Identifier):
                calls.add(node.callee.name)
            else:
                calls.add("<unknown>")
            # The callee may read or write global state, including an array cell.
            if conservative_calls:
                reads.update(bindings.globals)
                writes.update(bindings.globals)
        pending.extend(child for _, child in ast_children(node))
    return Effects(frozenset(reads), frozenset(writes), frozenset(definite), frozenset(calls), array_access)


@dataclass(frozen=True, order=True, slots=True)
class Definition:
    site: int
    binding: str


@dataclass(slots=True)
class Reaching:
    graph: Graph
    effects: tuple[Effects, ...]
    incoming: list[frozenset[Definition]]
    complete: bool

    def for_binding(self, site: int, binding: str):
        return tuple(sorted(definition for definition in self.incoming[site] if definition.binding == binding))

    def use_defs(self, site, binding):
        incoming = set(self.for_binding(site, binding))
        # Reads inside unordered subexpressions may see the current block's writes.
        if binding in self.effects[site].writes:
            incoming.add(Definition(site, binding))
        return incoming

    def return_slice(self, site, deadline):
        pending = [definition for binding in sorted(self.effects[site].reads)
                   for definition in sorted(self.use_defs(site, binding))]
        found = set()
        while pending:
            if len(found) >= MAX_SLICE or monotonic() >= deadline:
                return tuple(sorted(found)), False
            definition = pending.pop()
            if definition not in found:
                found.add(definition)
                if definition.site != self.graph.entry:
                    pending.extend(previous for binding in sorted(self.effects[definition.site].reads)
                                   for previous in sorted(self.use_defs(definition.site, binding))
                                   if previous not in found)
        return tuple(sorted(found)), self.complete


def reaching_definitions(graph, function, bindings, deadline):
    block_effects = tuple(effects(block.expression, bindings) for block in graph.blocks)
    # A path bypassing a declaration retains its entry-unknown definition.
    declarations = [block.syntax for block in graph.blocks
                    if isinstance(block.syntax, (ast.VariableDeclaration, ast.ArrayDeclaration))]
    seeds = bindings.globals | {binding for node in [*function.parameters, *declarations]
                                if (binding := bindings.declaration(node))}
    generated = tuple(frozenset(Definition(block.id, name) for name in (effect.writes | seeds if block.id == graph.entry else effect.writes))
                      for block, effect in zip(graph.blocks, block_effects, strict=True))
    predecessors = defaultdict(list)
    outgoing = graph.outgoing()
    for edge in graph.edges:
        predecessors[edge.target].append(edge.source)
    incoming = [frozenset() for _ in graph.blocks]
    results = incoming.copy()
    work, queued = deque([graph.entry]), {graph.entry}
    visited = set()
    for _ in range(MAX_TRANSFERS):
        if not work or monotonic() >= deadline:
            break
        site = work.popleft()
        queued.remove(site)
        before = frozenset().union(*(results[parent] for parent in predecessors[site]))
        incoming[site] = before
        after = generated[site] | frozenset(item for item in before if item.binding not in block_effects[site].definite)
        if after != results[site] or site not in visited:
            visited.add(site)
            results[site] = after
            for edge in outgoing[site]:
                if edge.target not in queued:
                    work.append(edge.target)
                    queued.add(edge.target)
    return Reaching(graph, block_effects, incoming, not work)
