"""Conservative evidence gates for the existing Phase 5 hypotheses."""
from time import monotonic

from compiler import ast_nodes as ast

from .intention_candidates import Evidence
from .intention_phase5 import Dependencies

RULES = frozenset({"LOOP_PROGRESS_BINDING", "FIXED_ARRAY_EDGE", "ARGUMENT_ROLE_PERMUTATION",
                   "ACCUMULATOR_CONSISTENCY"})


def definitely_unreachable(context, row):
    """Recognize literal dead branches and simple unconditional block transfers."""
    while row.parent_id is not None:
        parent = context.nodes[row.parent_id]
        node = parent.node
        if isinstance(node, ast.IfStatement) and isinstance(node.condition, ast.Literal):
            value = node.condition.value
            if row.relation == "then_branch" and value is False:
                return node.condition
            if row.relation == "else_branch" and value is True:
                return node.condition
        if isinstance(node, ast.Block):
            for statement in node.statements:
                if statement is row.node:
                    break
                if isinstance(statement, (ast.ReturnStatement, ast.BreakStatement, ast.ContinueStatement)):
                    return statement
        row = parent
    return None


def unconditional_transfer(statement):
    if isinstance(statement, (ast.ReturnStatement, ast.BreakStatement)):
        return statement
    if isinstance(statement, ast.Block):
        for child in statement.statements:
            if not isinstance(child, (ast.ExpressionStatement, ast.VariableDeclaration, ast.ArrayDeclaration,
                                      ast.ReturnStatement, ast.BreakStatement)):
                break
            exit_node = unconditional_transfer(child)
            if exit_node:
                return exit_node
    return None


def additive_return(context, row):
    while row.parent_id is not None:
        row = context.nodes[row.parent_id]
        if isinstance(row.node, ast.ReturnStatement):
            return row.node
        if not isinstance(row.node, ast.BinaryExpression) or row.node.operator != "+":
            break
    return None


def symmetric_callee(context, call):
    """Recognize a two-parameter pure commutative expression."""
    if len(call.arguments) != 2 or not isinstance(call.callee, ast.Identifier):
        return False
    function = next((row.node for row in context.nodes if isinstance(row.node, ast.FunctionDefinition)
                     and row.node.name == call.callee.name), None)
    if not function or len(function.body.statements) != 1:
        return False
    statement = function.body.statements[0]
    expression = statement.value if isinstance(statement, ast.ReturnStatement) else None
    return (isinstance(expression, ast.BinaryExpression) and expression.operator in {"+", "*", "==", "!="}
            and isinstance(expression.left, ast.Identifier) and isinstance(expression.right, ast.Identifier)
            and {expression.left.name, expression.right.name} == {p.name for p in function.parameters})


def gate_one(context, proposal, at_span, flow):
    category = proposal.category
    evidence = proposal.evidence
    if category == "ACCUMULATOR_CONSISTENCY":
        return Evidence("MISSING_SIGN_REQUIREMENT", "Distinct inputs may legitimately have different signs. Supply the intended contribution signs.", evidence[1].span)
    if category == "FIXED_ARRAY_EDGE":
        row = at_span.get((evidence[1].span, ast.Literal))
        dead = definitely_unreachable(context, row) if row else None
        if dead:
            return Evidence("UNREACHABLE_ACCESS", "A literal branch or block transfer excludes this access.", dead.span)
    if category == "LOOP_PROGRESS_BINDING":
        row = at_span.get((evidence[1].span, ast.Identifier))
        if row and row.parent_id is not None:
            update = context.nodes[row.parent_id]
            loop_record = context.nodes[update.parent_id]
            loop = loop_record.node
            dead = definitely_unreachable(context, loop_record)
            exit_node = dead or unconditional_transfer(loop.body)
            if exit_node:
                return Evidence("LOOP_EXITS_BEFORE_UPDATE", "This path excludes repeating the loop update.", exit_node.span)
            counter = flow.bindings.get(id(row.node))
            if counter:
                after = flow.end[loop_record.node_id]
                if any(flow.order[node_id] >= after and symbol.id == counter.id
                       for node_id, symbol in flow.bindings.items()):
                    return Evidence("COUNTER_HAS_LATER_USES", "Changing this counter would also change a binding used after the loop.", row.node.span)
    if category == "ARGUMENT_ROLE_PERMUTATION":
        peer = at_span.get((evidence[0].span, ast.FunctionCall))
        outlier = at_span.get((evidence[1].span, ast.FunctionCall))
        if not peer or not outlier:
            return Evidence("MISSING_CALL_ROLE", "A shared result role could not be established.", evidence[1].span)
        if symmetric_callee(context, outlier.node):
            return Evidence("SYMMETRIC_CALLEE", "Swapping the two arguments preserves this callee's direct result.", outlier.node.span)
        shared = additive_return(context, peer)
        if shared is None or shared is not additive_return(context, outlier):
            return Evidence("DISTINCT_CALL_CONTEXT", "These calls do not share one unweighted additive return expression.", outlier.node.span)
        symbols = [flow.bindings.get(id(arg)) for arg in outlier.node.arguments]
        if (any(symbol is None or not flow.unchanged_in(symbol, shared) for symbol in symbols)
                or any(symbol.scope_id == context.scopes[0].id for symbol in symbols)):
            return Evidence("UNKNOWN_ARGUMENT_STABILITY", "The argument bindings may change across evaluations.", outlier.node.span)
    return None


def apply_precision_gates(context, proposals, deadline, rules=RULES):
    """Partition existing hypotheses into evidence-backed and withheld rows."""
    if not proposals:
        return (), (), False
    accepted = []
    withheld = []
    at_span = {(row.node.span, type(row.node)): row for row in context.nodes}
    flow = Dependencies.from_context(context)
    for index, proposal in enumerate(proposals):
        if monotonic() >= deadline:
            withheld.extend((row, Evidence("ANALYSIS_LIMIT", "The evidence check reached its analysis limit."))
                            for row in proposals[index:])
            return tuple(accepted), tuple(withheld), True
        reason = gate_one(context, proposal, at_span, flow) if proposal.category in rules else None
        if reason:
            withheld.append((proposal, reason))
        else:
            accepted.append(proposal)
    return tuple(accepted), tuple(withheld), False
