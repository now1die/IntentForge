"""Finite must/may initialization and path facts over compiled Mini-C bindings."""
from collections import deque
from dataclasses import dataclass
from time import monotonic

from compiler import ast_nodes as ast
from compiler.symbol_table import SymbolKind

from .dataflow import MAX_TRANSFERS, effects

MAX_TRACKED_CELLS = 32
REVERSE = {"<": ">", "<=": ">=", ">": "<", ">=": "<=", "==": "==", "!=": "!="}
NEGATE = {"<": ">=", "<=": ">", ">": "<=", ">=": "<", "==": "!=", "!=": "=="}


def scalar(node):
    if isinstance(node, ast.Literal):
        return node.value
    if isinstance(node, ast.UnaryExpression) and node.operator == "-" and isinstance(node.operand, ast.Literal):
        if type(node.operand.value) is int:
            return -node.operand.value
    return None


def binding(index, node):
    symbol = index.identifiers.get(id(node))
    return symbol.id if symbol else None


def extent(node):
    size = scalar(node.size)
    return size if type(size) is int and 0 < size <= MAX_TRACKED_CELLS else None


def comparison(index, node):
    if not isinstance(node, ast.BinaryExpression) or node.operator not in REVERSE:
        return None
    for left, operator, right in ((node.left, node.operator, node.right),
                                  (node.right, REVERSE[node.operator], node.left)):
        key, value = binding(index, left), scalar(right)
        if key and type(value) is int:
            return key, operator, value
    return None


def implications(index, node, truth):
    """Retain conditions guaranteed on the selected short-circuit edge."""
    if isinstance(node, ast.BinaryExpression) and (node.operator, truth) in {("&&", True), ("||", False)}:
        yield from implications(index, node.left, truth)
        yield from implications(index, node.right, truth)
    elif fact := comparison(index, node):
        key, operator, value = fact
        yield key, operator if truth else NEGATE[operator], value


@dataclass(frozen=True, slots=True)
class State:
    must: frozenset = frozenset()
    may: frozenset = frozenset()
    constants: frozenset = frozenset()
    paths: frozenset = frozenset()

    def join(self, other):
        return State(self.must & other.must, self.may | other.may,
                     self.constants & other.constants, self.paths & other.paths)

    def initialization(self, slot):
        if slot in self.must:
            return "INITIALIZED"
        return "MAYBE_INITIALIZED" if slot in self.may else "UNINITIALIZED"


def target_slot(index, node, arrays):
    if isinstance(node, ast.ArrayAccess):
        key, position = binding(index, node.array), scalar(node.index)
        if key in arrays and type(position) is int and 0 <= position < arrays[key]:
            return key, position
    elif (symbol := index.identifiers.get(id(node))) and symbol.kind in {SymbolKind.VARIABLE, SymbolKind.PARAMETER}:
        return symbol.id, None
    return None


def transfer(block, state, effect, index, arrays):
    node = block.expression
    if isinstance(node, ast.ExpressionStatement):
        node = node.expression
    writes = effect.writes
    must, may = set(state.must), set(state.may)
    constants = {pair for pair in state.constants if pair[0][0] not in writes}
    paths = frozenset(fact for fact in state.paths if fact[0] not in writes)
    slot, value = None, None
    if isinstance(node, (ast.VariableDeclaration, ast.ArrayDeclaration)):
        key = index.declaration(node)
        must = {item for item in must if item[0] != key}
        may = {item for item in may if item[0] != key}
        if isinstance(node, ast.VariableDeclaration) and node.initializer is not None:
            slot, value = (key, None), scalar(node.initializer)
    else:
        # Expression writes might be skipped. They can add possible
        # initialization, but never remove an initialized local slot.
        for key in writes - index.globals:
            if key in arrays:
                may.update((key, i) for i in range(arrays[key]))
            else:
                may.add((key, None))
        if isinstance(node, ast.Assignment) and node.operator == "=":
            slot, value = target_slot(index, node.target, arrays), scalar(node.value)
            if isinstance(node.target, ast.ArrayAccess) and slot:
                key, _ = slot
                # A direct literal-index store can affect only one cell
                # when neither the index nor the RHS writes this array.
                if key not in effects(node.value, index).writes:
                    may.difference_update(item for item in tuple(may) if item[0] == key and item not in state.may)
                    constants.update(pair for pair in state.constants if pair[0][0] == key and pair[0] != slot)
    if slot and slot[0] and slot[0] not in index.globals:
        must.add(slot)
        may.add(slot)
        if value is not None:
            constants.add((slot, type(value).__name__, value))
    return State(frozenset(must), frozenset(may), frozenset(constants), paths)


def propagate(item, index, deadline):
    flow, graph = item.flow, item.flow.graph
    arrays = {key: size for block in graph.blocks if isinstance(block.syntax, ast.ArrayDeclaration)
              if (key := index.declaration(block.syntax)) and (size := extent(block.syntax))}
    parameters = frozenset((index.declaration(node), None) for node in item.function.parameters)
    incoming = {graph.entry: State(parameters, parameters)}
    edges = graph.outgoing()
    pending, queued = deque([graph.entry]), {graph.entry}
    for _ in range(MAX_TRANSFERS):
        if not pending:
            return incoming, arrays
        if monotonic() >= deadline:
            break
        site = pending.popleft()
        queued.remove(site)
        block = graph.blocks[site]
        effect = flow.effects[site]
        after = transfer(block, incoming[site], effect, index, arrays)
        for edge in edges[site]:
            facts = after.paths
            if edge.kind in {"true", "false"} and not (effect.writes or effect.calls):
                facts = facts | frozenset((*fact, site, edge.kind)
                    for fact in implications(index, block.expression, edge.kind == "true"))
            out = State(after.must, after.may, after.constants, facts)
            previous = incoming.get(edge.target)
            merged = out if previous is None else previous.join(out)
            if merged != previous:
                incoming[edge.target] = merged
                if edge.target not in queued:
                    pending.append(edge.target)
                    queued.add(edge.target)
    return None, arrays
