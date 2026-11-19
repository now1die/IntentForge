"""Adapters retaining each compiler's native evidence and node names."""
from ai.intention_context import build_context
from compiler.ast_nodes import (
    ArrayDeclaration, ForStatement, FunctionDefinition, Identifier, IfStatement, Parameter,
    ReturnStatement, VariableDeclaration, WhileStatement,
)

from .contract import Diagnostic, EvidenceReport, EvidenceUnit, Node, ScopeEvidence
from .source_map import SourceMap

MINI_DECLARATIONS = (FunctionDefinition, VariableDeclaration, Parameter, ArrayDeclaration)
MINI_FLOW = (IfStatement, ForStatement, WhileStatement, ReturnStatement)
CLANG_SCOPES = {"FUNCTION_DECL", "COMPOUND_STMT", "FOR_STMT", "STRUCT_DECL", "UNION_DECL", "ENUM_DECL"}
CLANG_FLOW = {"IF_STMT", "FOR_STMT", "WHILE_STMT", "DO_STMT", "RETURN_STMT", "SWITCH_STMT",
              "BREAK_STMT", "CONTINUE_STMT", "GOTO_STMT"}


def minic(source: str) -> EvidenceReport:
    context = build_context(source)
    file = "main.mc"
    mapper = SourceMap(source, file)
    scope_ids = {scope.id: index for index, scope in enumerate(context.scopes)}
    scopes = [ScopeEvidence(id=scope_ids[scope.id], kind=scope.kind.value,
                            parent=scope_ids[scope.parent.id] if scope.parent else None,
                            span=mapper.span(scope.span)) for scope in context.scopes]
    declarations = {record.node.span: record.node_id for record in context.nodes
                    if isinstance(record.node, MINI_DECLARATIONS)}
    symbols = {sym.declaration_span: sym for scope in context.scopes for sym in scope.symbols.values()}
    nodes, control = [], []
    for record in context.nodes:
        node = record.node
        scope = context.scope_at(node.span.start.offset)
        symbol = symbols.get(node.span) if isinstance(node, MINI_DECLARATIONS) else None
        binding = context.visible_at(node.span.start.offset).get(node.name) if isinstance(node, Identifier) else None
        observed = context.semantic.expression_types.get(id(node)) if context.semantic else None
        node_type = observed or ((symbol or binding).type if (symbol or binding) else None)
        display = node_type.display() if node_type and not node_type.is_error else None
        signature = {}
        if isinstance(node, FunctionDefinition):
            signature = {"parameter_types": [item.type_name for item in node.parameters],
                         "result_type": node.return_type, "variadic": False}
        nodes.append(Node(id=record.node_id, parent=record.parent_id, kind=type(node).__name__,
                          name=getattr(node, "name", None), declaration=isinstance(node, MINI_DECLARATIONS),
                          span=mapper.span(node.span), scope=scope_ids[scope.id] if scope else None,
                          reference=declarations.get(binding.declaration_span) if binding else None,
                          type=display, canonical_type=display, **signature))
        if isinstance(node, MINI_FLOW):
            control.append(record.node_id)
    diagnostic_groups = (
        ("lexical", context.parsed.lexical_errors), ("syntax", context.parsed.syntax_errors),
        ("semantic", context.semantic.diagnostics if context.semantic else ()),
    )
    diagnostics = [
        Diagnostic(severity="error", message=diag.message, code=getattr(diag, "code", None),
                   category=phase,
                   phase=phase, span=mapper.span(diag.span))
        for phase, group in diagnostic_groups for diag in group
    ]
    return EvidenceReport(language="mini-c", provider="ply-mini-c",
                          status="ok" if context.compiler_valid else "compiler_errors",
                          files=[file], units=[EvidenceUnit(entry=file, ast="available" if nodes else "unavailable",
                                                            diagnostics=diagnostics, nodes=nodes, scopes=scopes,
                                                            control_flow_nodes=control)],
                          unsupported=["runtime_execution", "control_flow_graph"])


def clang(result) -> EvidenceReport:
    units = []
    for unit in result.units:
        scopes = [ScopeEvidence(id=node.id, kind=node.kind, parent=node.scope, span=node.span)
                  for node in unit.nodes if node.kind in CLANG_SCOPES]
        units.append(EvidenceUnit(entry=unit.entry, ast=unit.ast, diagnostics=unit.diagnostics, nodes=unit.nodes,
                                  scopes=scopes, control_flow_nodes=[node.id for node in unit.nodes
                                                                    if node.kind in CLANG_FLOW]))
    return EvidenceReport(language="c", provider="clang", version=result.version, detail=result.detail,
                          status=result.status, files=result.files, units=units,
                          unsupported=["runtime_execution", "intelligent_repair", "linking", "control_flow_graph"])
