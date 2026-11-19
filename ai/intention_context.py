"""Observed, source-located context from the existing Mini-C compiler."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, fields
from typing import Any

from compiler.ast_nodes import ASTNode, FunctionDefinition, Identifier
from compiler.lexer import tokenize
from compiler.parser import ParseResult, parse
from compiler.semantic_analyzer import SemanticResult, analyze_semantics
from compiler.source_location import SourceSpan
from compiler.symbol_table import Scope, Symbol


MAX_SOURCE = 24_000
MAX_TOKENS = 3_000
MAX_NESTING = 48


class ContextLimit(ValueError):
    """The input exceeds the bounded intention-analysis policy."""


@dataclass(frozen=True, slots=True)
class Example:
    args: tuple[int | bool, ...]
    expected_return: int | bool


@dataclass(frozen=True, slots=True)
class Requirement:
    function: str | None = None
    description: str | None = None
    return_expression: str | None = None
    condition: str | None = None
    return_ordinal: int | None = None
    condition_ordinal: int | None = None
    examples: tuple[Example, ...] = ()


@dataclass(frozen=True, slots=True)
class NodeContext:
    node_id: int
    node: ASTNode
    parent_id: int | None
    relation: str | None
    function: FunctionDefinition | None


def enclosing(span: SourceSpan, offset: int) -> bool:
    return span.start.offset <= offset < span.end.offset


def overlapping(left: SourceSpan, right: SourceSpan) -> bool:
    return left.start.offset < right.end.offset and right.start.offset < left.end.offset


def ast_children(node: ASTNode):
    for descriptor in fields(node):
        member = getattr(node, descriptor.name)
        if isinstance(member, ASTNode):
            yield descriptor.name, member
        elif isinstance(member, list):
            yield from ((descriptor.name, item) for item in member if isinstance(item, ASTNode))


@dataclass(slots=True)
class IntentionContext:
    source: str
    parsed: ParseResult
    semantic: SemanticResult | None
    nodes: list[NodeContext]
    requirement: Requirement | None
    scopes: tuple[Scope, ...]

    @property
    def compiler_valid(self) -> bool:
        return self.parsed.valid and self.semantic is not None and self.semantic.success

    @property
    def diagnostics(self):
        return [*self.parsed.lexical_errors, *self.parsed.syntax_errors,
                *(self.semantic.diagnostics if self.semantic else ())]

    def text(self, span: SourceSpan) -> str:
        return self.source[span.start.offset:span.end.offset]

    def scope_at(self, offset: int) -> Scope | None:
        return next((scope for scope in reversed(self.scopes) if scope.span and enclosing(scope.span, offset)),
                    self.scopes[0] if self.scopes else None)

    def visible_at(self, offset: int) -> dict[str, Symbol]:
        visible = {}
        scope = self.scope_at(offset)
        while scope is not None:
            for name, symbol in scope.symbols.items():
                if not scope.parent or symbol.declaration_span.start.offset < offset:
                    visible.setdefault(name, symbol)
            scope = scope.parent
        return visible

    def expected_type(self, record: NodeContext) -> str | None:
        for diagnostic in self.semantic.diagnostics if self.semantic else ():
            if diagnostic.expected_type and diagnostic.span == record.node.span:
                return diagnostic.expected_type
        return None

    def to_dict(self) -> dict[str, Any]:
        observed = []
        children = defaultdict(list)
        for record in self.nodes:
            children[record.parent_id].append(record.node_id)
        for record in self.nodes:
            node = record.node
            offset = node.span.start.offset
            scope = self.scope_at(offset)
            inferred_type = self.semantic.expression_types.get(id(node)) if self.semantic else None
            binding = self.visible_at(offset).get(node.name) if isinstance(node, Identifier) else None
            observed.append({
                "id": record.node_id, "kind": type(node).__name__, "span": node.span.to_dict(),
                "parent": record.parent_id, "children": children[record.node_id], "relation": record.relation,
                "function": record.function.name if record.function else None,
                "scope": scope.id if scope else None,
                "type": inferred_type.display() if inferred_type else binding.type.display() if binding else None,
                "expected_type": self.expected_type(record),
                "name": getattr(node, "name", None), "operator": getattr(node, "operator", None),
                "binding": binding.id if binding else None,
            })
        return {
            "ast_status": "AVAILABLE" if self.parsed.valid else "MISSING_INCOMPLETE_SYNTAX",
            "semantic_status": "AVAILABLE" if self.semantic else "MISSING_INCOMPLETE_SYNTAX",
            "nodes": observed,
            "symbols": [symbol.to_dict() for scope in self.scopes for symbol in scope.symbols.values()],
            "scopes": [{"id": scope.id, "kind": scope.kind.value, "parent": scope.parent.id if scope.parent else None,
                        "span": scope.span.to_dict() if scope.span else None} for scope in self.scopes],
            "tokens": [token.to_dict() for token in self.parsed.tokens] if not self.parsed.valid else [],
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
            "user_requirement": asdict(self.requirement) if self.requirement else None,
        }


def build_context(source: str, requirement: Requirement | None = None) -> IntentionContext:
    if len(source) > MAX_SOURCE:
        raise ContextLimit("Source exceeds the intention-analysis character limit.")
    tokens, _ = tokenize(source)
    if len(tokens) > MAX_TOKENS:
        raise ContextLimit("Source exceeds the intention-analysis token limit.")
    depth = expression_tokens = 0
    for token in tokens:
        if token.lexeme in {"(", "[", "{"}:
            depth += 1
        elif token.lexeme in {")", "]", "}"}:
            depth = max(0, depth - 1)
        expression_tokens = 0 if token.lexeme in {";", "{", "}"} else expression_tokens + 1
        if depth > MAX_NESTING or expression_tokens > 180:
            raise ContextLimit("Source exceeds the nesting or expression limit.")
    parsed = parse(source)
    semantic = analyze_semantics(parsed.ast) if parsed.valid and parsed.ast else None
    records: list[NodeContext] = []
    stack = [(parsed.ast, None, None, None)] if parsed.valid and parsed.ast else []
    while stack:
        node, parent, relation, function = stack.pop()
        function = node if isinstance(node, FunctionDefinition) else function
        record = NodeContext(len(records), node, parent, relation, function)
        records.append(record)
        stack.extend((child, record.node_id, edge, function) for edge, child in reversed(list(ast_children(node))))
    return IntentionContext(source, parsed, semantic, records, requirement,
                            tuple(semantic.symbol_table.all_scopes()) if semantic else ())
