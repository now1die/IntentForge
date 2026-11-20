"""Bounded, binding-aware structural hypotheses for compiler-valid Mini-C."""

from bisect import bisect_left
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import groupby, islice
from time import monotonic

from compiler import ast_nodes as ast
from compiler.symbol_table import Symbol, SymbolKind

from .intention_candidates import Edit, Evidence, Proposal
from .intention_context import IntentionContext

MAX_NODES = 1_200
MAX_HYPOTHESES = 6
ORDERED = {"<", "<=", ">", ">="}


@dataclass(slots=True)
class Dependencies:
    bindings: dict[int, Symbol]
    order: dict[int, int]
    end: list[int]
    writes: dict[str, list[int]]

    @classmethod
    def from_context(cls, context):
        bindings = {}
        order = {id(row.node): row.node_id for row in context.nodes}
        end = [row.node_id + 1 for row in context.nodes]
        for row in reversed(context.nodes):
            if row.parent_id is not None:
                end[row.parent_id] = max(end[row.parent_id], end[row.node_id])
        for row in context.nodes:
            if isinstance(row.node, ast.Identifier):
                symbol = context.visible_at(row.node.span.start.offset).get(row.node.name)
                if symbol:
                    bindings[id(row.node)] = symbol
        writes = defaultdict(list)
        for row in context.nodes:
            node = row.node
            target = node.target if isinstance(node, ast.Assignment) else (
                node.operand if isinstance(node, ast.UpdateExpression) else None)
            symbol = bindings.get(id(target))
            if symbol:
                writes[symbol.id].append(row.node_id)
        return cls(bindings, order, end, writes)

    def unchanged_in(self, symbol, node):
        left = self.order[id(node)]
        writes = self.writes.get(symbol.id, ())
        index = bisect_left(writes, left)
        return index == len(writes) or writes[index] >= self.end[left]


def loop_progress(loop, flow):
    if not isinstance(loop.initializer, ast.VariableDeclaration) or not isinstance(loop.update, ast.UpdateExpression):
        return None
    guard = loop.condition
    if (not isinstance(guard, ast.BinaryExpression) or guard.operator not in ORDERED
            or not isinstance(guard.left, ast.Identifier) or not isinstance(guard.right, (ast.Identifier, ast.Literal))
            or not isinstance(loop.update.operand, ast.Identifier)):
        return None
    index = flow.bindings.get(id(guard.left))
    updated = flow.bindings.get(id(loop.update.operand))
    direction = "++" if guard.operator in {"<", "<="} else "--"
    if (not index or not updated or index.id == updated.id or index.name != loop.initializer.name
            or index.kind != SymbolKind.VARIABLE or index.type.display() != "int"
            or index.declaration_span.start.offset != loop.initializer.span.start.offset
            or loop.initializer.initializer is None or loop.update.operator != direction
            or not flow.unchanged_in(index, loop.body)):
        return None
    return Proposal((Edit(loop.update.operand.span, index.name),), "LOOP_PROGRESS_BINDING", (
        Evidence("BINDING_DEPENDENCY", "The guard reads the initialized loop binding, which the body never writes.", guard.left.span),
        Evidence("PROGRESS_MISMATCH", "The unit update writes a different lexical binding.", loop.update.operand.span),
    ), "The guarded index may be the intended target of the update.", "UpdateExpression", "update", type_match=True)


def array_edge(node, flow):
    if not isinstance(node.index, ast.Literal) or type(node.index.value) is not int:
        return None
    binding = flow.bindings.get(id(node.array))
    if not binding or binding.kind != SymbolKind.ARRAY or not binding.array_size or node.index.value != binding.array_size:
        return None
    return Proposal((Edit(node.index.span, str(binding.array_size - 1)),), "FIXED_ARRAY_EDGE", (
        Evidence("BINDING_DEPENDENCY", f"The visible array has {binding.array_size} cells.", binding.declaration_span),
        Evidence("INDEX_BOUNDARY", "The literal index equals the array length.", node.index.span),
    ), "If the access intends the last cell, use the highest valid index.", "ArrayAccess", "index", type_match=True)


def argument_roles(calls):
    for peers in calls.values():
        votes = Counter(signature for _, signature in peers)
        if len(votes) != 2:
            continue
        (common, support), (outlier, minority) = votes.most_common()
        if support < 2 or minority != 1:
            continue
        node = next(node for node, sig in peers if sig == outlier)
        by_binding = dict(zip(outlier, node.arguments, strict=True))
        edits = tuple(Edit(argument.span, by_binding[expected].name)
                      for argument, present, expected in zip(node.arguments, outlier, common, strict=True)
                      if present != expected)
        if len(edits) != 2:
            continue
        peer = next(node for node, sig in peers if sig == common)
        yield Proposal(edits, "ARGUMENT_ROLE_PERMUTATION", (
            Evidence("CALL_ROLE_CONSENSUS", f"{support} calls in this function use the same order for these bindings.", peer.span),
            Evidence("BINDING_DEPENDENCY", "This direct call reverses two of the same identifiers.", node.span),
        ), "All these calls may be intended to use the same argument roles.", "FunctionCall", "arguments", type_match=True)


def accumulation(block, flow):
    def update(statement):
        node = statement.expression if isinstance(statement, ast.ExpressionStatement) else None
        if not isinstance(node, ast.Assignment) or node.operator not in {"+=", "-="}:
            return None, None, None
        target = flow.bindings.get(id(node.target))
        value = flow.bindings.get(id(node.value))
        if (not target or target.kind != SymbolKind.VARIABLE or target.type.display() != "int"
                or not value or value.kind != SymbolKind.PARAMETER or value.type.display() != "int"):
            return None, None, None
        return target.id, node, value.id

    for binding, segment in groupby(map(update, block.statements), key=lambda row: row[0]):
        if binding is None:
            continue
        rows = list(segment)
        if len(rows) < 4 or len(rows) > 12 or len({value for _, _, value in rows}) != len(rows):
            continue
        votes = Counter(node.operator for _, node, _ in rows)
        if len(votes) != 2:
            continue
        (common, support), (outlier, minority) = votes.most_common()
        if support < 3 or minority > 2 or support < 2 * minority:
            continue
        mismatches = [node for _, node, _ in rows if node.operator == outlier]
        peer = next(node for _, node, _ in rows if node.operator == common)
        edits = tuple(Edit(node.span, f"{node.target.name} {common} {node.value.name}") for node in mismatches)
        yield Proposal(edits, "ACCUMULATOR_CONSISTENCY", (
            Evidence("UPDATE_CONSENSUS", f"{support} adjacent updates to this binding use {common}.", peer.span),
            *(Evidence("BINDING_DEPENDENCY", f"This update uses {outlier} with a distinct integer parameter.", node.span)
              for node in mismatches),
        ), "The adjacent parameters may be contributions with the same sign.", "Assignment", "update", type_match=True)


def scan(context: IntentionContext, deadline):
    if not context.compiler_valid:
        return "INCOMPLETE_COMPILER_EVIDENCE", ()
    if len(context.nodes) > MAX_NODES or monotonic() >= deadline:
        return "SCAN_LIMITED", ()
    flow = Dependencies.from_context(context)
    calls = defaultdict(list)
    findings = []
    for row in context.nodes:
        if monotonic() >= deadline or len(findings) >= MAX_HYPOTHESES:
            return "SCAN_LIMITED", tuple(findings)
        node = row.node
        if isinstance(node, ast.ForStatement):
            proposal = loop_progress(node, flow)
            if proposal:
                findings.append(proposal)
        elif isinstance(node, ast.ArrayAccess):
            proposal = array_edge(node, flow)
            if proposal:
                findings.append(proposal)
        elif isinstance(node, ast.Block):
            findings.extend(islice(accumulation(node, flow), MAX_HYPOTHESES - len(findings)))
        elif isinstance(node, ast.FunctionCall) and row.function and 2 <= len(node.arguments) <= 4:
            callee = flow.bindings.get(id(node.callee))
            symbols = [flow.bindings.get(id(arg)) for arg in node.arguments]
            if callee and callee.kind == SymbolKind.FUNCTION and all(symbols):
                signature = tuple(symbol.id for symbol in symbols)
                if len(set(signature)) == len(signature):
                    calls[(row.function.span.start.offset, callee.id, frozenset(signature))].append((node, signature))
    available = MAX_HYPOTHESES - len(findings)
    call_findings = tuple(islice(argument_roles(calls), available + 1))
    status = "SCAN_LIMITED" if len(call_findings) > available else "HEURISTIC_SCAN"
    return status, (*findings, *call_findings[:available])


def evidence_order(pool):
    """Experimental stable ordering within compiler/specification strata."""
    strength = {"PROGRESS_MISMATCH": 3, "INDEX_BOUNDARY": 3, "CALL_ROLE_CONSENSUS": 2, "UPDATE_CONSENSUS": 1}
    return sorted(pool, key=lambda row: (
        not row.compiler_valid, -row.proposal.specification_matches, row.remaining_diagnostics,
        -max((strength.get(fact.kind, 0) for fact in row.proposal.evidence), default=0),
    ))
