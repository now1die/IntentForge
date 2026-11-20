"""Bounded statement-level control flow for the compiler's structured Mini-C AST."""
from dataclasses import dataclass, field

from compiler import ast_nodes as ast

MAX_BLOCKS = 220
MAX_EDGES = 440


class FlowLimit(ValueError):
    """The graph could not be built within the analysis envelope."""


@dataclass(frozen=True, slots=True)
class Block:
    id: int
    kind: str
    syntax: ast.ASTNode
    expression: ast.ASTNode | None = None

    def to_dict(self, reachable):
        return {"id": self.id, "kind": self.kind, "span": self.syntax.span.to_dict(),
                "reachable": self.id in reachable}


@dataclass(frozen=True, slots=True)
class Edge:
    source: int
    target: int
    kind: str


@dataclass(slots=True)
class Graph:
    blocks: list[Block] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)

    def add(self, kind, syntax, expression=None):
        if len(self.blocks) >= MAX_BLOCKS:
            raise FlowLimit("CFG block limit")
        block = Block(len(self.blocks), kind, syntax, expression)
        self.blocks.append(block)
        return block.id

    def link(self, source, target, kind="next"):
        if len(self.edges) >= MAX_EDGES:
            raise FlowLimit("CFG edge limit")
        self.edges.append(Edge(source, target, kind))

    @property
    def entry(self):
        return 0

    @property
    def exit(self):
        return 1

    def outgoing(self):
        rows = [[] for _ in self.blocks]
        for edge in self.edges:
            rows[edge.source].append(edge)
        return rows

    def reachable(self):
        outgoing = self.outgoing()
        pending, seen = [self.entry], set()
        while pending:
            visit = pending.pop()
            if visit not in seen:
                seen.add(visit)
                pending.extend(edge.target for edge in outgoing[visit])
        return seen

    def to_dict(self):
        reachable = self.reachable()
        return {"entry": self.entry, "exit": self.exit,
                "blocks": [row.to_dict(reachable) for row in self.blocks],
                "edges": [{"source": edge.source, "target": edge.target, "kind": edge.kind} for edge in self.edges]}


def literal_condition(expression):
    if isinstance(expression, ast.Literal) and type(expression.value) is bool:
        return expression.value
    return None


def build_graph(function: ast.FunctionDefinition):
    """Lower structured control to basic blocks of at most one statement/expression."""
    graph = Graph()
    graph.add("entry", function)
    graph.add("exit", function)

    def branch(header, condition, true, false, *, infinite=False):
        value = True if infinite else literal_condition(condition)
        if value is not False:
            graph.link(header, true, "true")
        if value is not True:
            graph.link(header, false, "false")

    def lower(statement, after, loops=None):
        if isinstance(statement, ast.Block):
            target = after
            for child in reversed(statement.statements):
                target = lower(child, target, loops)
            return target
        if isinstance(statement, ast.IfStatement):
            header = graph.add("branch", statement, statement.condition)
            yes = lower(statement.then_branch, after, loops)
            no = lower(statement.else_branch, after, loops) if statement.else_branch else after
            branch(header, statement.condition, yes, no)
            return header
        if isinstance(statement, (ast.ForStatement, ast.WhileStatement)):
            header = graph.add("loop_header", statement, statement.condition)
            # A latch remains explicit even with an empty update or body.
            update = statement.update if isinstance(statement, ast.ForStatement) else None
            latch = graph.add("loop_latch", update or statement, update)
            graph.link(latch, header, "back")
            body = lower(statement.body, latch, (after, latch))
            branch(header, statement.condition, body, after, infinite=statement.condition is None)
            if isinstance(statement, ast.ForStatement) and statement.initializer:
                return lower(statement.initializer, header, loops)
            return header
        if isinstance(statement, ast.ReturnStatement):
            node = graph.add("return", statement, statement.value)
            graph.link(node, graph.exit, "return")
            return node
        if isinstance(statement, (ast.BreakStatement, ast.ContinueStatement)):
            if loops is None:
                raise FlowLimit("Unresolved loop transfer")
            is_break = isinstance(statement, ast.BreakStatement)
            kind = "break" if is_break else "continue"
            node = graph.add(kind, statement)
            graph.link(node, loops[0 if is_break else 1], kind)
            return node
        node = graph.add("statement", statement, statement)
        graph.link(node, after)
        return node

    graph.link(graph.entry, lower(function.body, graph.exit))
    return graph
