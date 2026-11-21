"""Bounded Phase 7.5 repairs over lexical definitions and recursive result paths."""
from dataclasses import dataclass
from itertools import islice
from operator import ge, gt, le, lt
from time import monotonic

from analysis_evidence.expression_normalization import normalized_comparison
from analysis_evidence.interprocedural import atom, descendants, local_initializer
from analysis_evidence.recursive_layout import guarded_layout
from compiler import ast_nodes as ast

from .intention_candidates import Edit, Evidence, Proposal

COMPONENTS = frozenset({"helper_layout", "nonunit", "dependencies"})
CATEGORIES = frozenset({"RECURSIVE_DEPENDENCY_PROGRESS", "NONUNIT_RECURSIVE_PROGRESS",
                        "RECURSIVE_TERM_COMBINATION", "HELPER_ARGUMENT_DEPENDENCY", "RADIX_PROGRESS_MISMATCH"})
ARITHMETIC = {"+", "-", "*", "/", "%"}
DIRECTION = {">": 1, ">=": 1, "<": -1, "<=": -1}
PREDICATES = {">": gt, ">=": ge, "<": lt, "<=": le}
MAX_NEW = 6


@dataclass(frozen=True, slots=True)
class Recurrence:
    guard: ast.IfStatement
    binding: str
    parameter: str
    position: int
    threshold: int
    comparison: str
    site: int
    value: ast.ASTNode
    calls: tuple[ast.FunctionCall, ...]


def selected_examples(function, examples):
    kinds = {"int": int, "bool": bool}
    return tuple(example for example in examples if len(example.args) == len(function.parameters)
                 and all(type(value) is kinds.get(parameter.type_name)
                         for value, parameter in zip(example.args, function.parameters, strict=True)))


def lexical_binding(node, bindings):
    return bindings.identifiers.get(id(node)) if isinstance(node, ast.Identifier) else None


def unalias(node, site, flow, bindings, helpers):
    for _ in range(8):
        binding = lexical_binding(node, bindings)
        declaration = local_initializer(flow, site, binding.id, bindings) if binding else None
        if declaration:
            site, node = declaration
            continue
        if isinstance(node, ast.FunctionCall) and isinstance(node.callee, ast.Identifier):
            helper = helpers.get(node.callee.name)
            if helper and helper["identity_parameter"] == 0 and len(node.arguments) == 1:
                node = node.arguments[0]
                continue
        break
    return node, site


def recurrence(context, item, bindings, path, helpers, deadline):
    function, flow = item.function, item.flow
    if not path.complete or not 1 <= len(function.parameters) <= 4:
        return None
    live = [block for block in flow.graph.blocks if path.incoming[block.id]]
    guards = [block for block in live if block.kind == "branch"]
    if len(guards) != 1 or len(live) > 24:
        return None
    guard = guards[0]
    condition = normalized_comparison(guard.expression, context.semantic.expression_types, bindings.identifiers)
    if (not condition or not isinstance(condition.left, ast.Identifier)
            or not isinstance(condition.right, ast.Literal) or condition.operator not in DIRECTION):
        return None
    parameter = lexical_binding(condition.left, bindings)
    positions = {bindings.declaration(p): i for i, p in enumerate(function.parameters)}
    if not parameter or parameter.id not in positions:
        return None
    layout = guarded_layout(item, path, bindings, condition, local_definitions=True, deadline=deadline)
    if not layout:
        return None
    branch, _, fallback, condition = layout
    block = next(block for block in live if block.syntax is fallback)
    calls = []
    for node_block in live:
        if node_block.kind == "return":
            expression = node_block.expression
        elif node_block.kind == "statement" and isinstance(node_block.syntax, ast.VariableDeclaration):
            expression = node_block.syntax.initializer
        else:
            continue
        for node in descendants(expression):
            if isinstance(node, ast.FunctionCall):
                if not isinstance(node.callee, ast.Identifier):
                    return None
                if node.callee.name == function.name:
                    if len(node.arguments) != len(function.parameters):
                        return None
                    calls.append(node)
                elif node.callee.name not in helpers:
                    return None
            elif isinstance(node, ast.Identifier):
                bound = lexical_binding(node, bindings)
                if not bound or bound.id in bindings.globals:
                    return None
            elif isinstance(node, ast.Literal):
                if type(node.value) not in {int, bool}:
                    return None
            elif not isinstance(node, ast.BinaryExpression) or node.operator not in ARITHMETIC:
                return None
    if not 1 <= len(calls) <= 2:
        return None
    sliced, complete = flow.return_slice(block.id, deadline)
    if not complete:
        return None
    dependencies = {id(node) for site in {block.id, *(definition.site for definition in sliced)}
                    for node in descendants(flow.graph.blocks[site].expression)}
    if any(id(call) not in dependencies for call in calls):
        return None
    return Recurrence(branch, parameter.id, parameter.name, positions[parameter.id], condition.right.value,
                      condition.operator, block.id, fallback.value, tuple(calls))


def argument_relation(argument, facts, bindings):
    relation = atom(argument, bindings)
    if relation and relation[0] == facts.binding:
        return {"offset": relation[2]}
    if isinstance(argument, ast.BinaryExpression) and argument.operator in {"+", "-"}:
        left, right = (lexical_binding(node, bindings) for node in (argument.left, argument.right))
        if left and left.id == facts.binding and right and right.id != facts.binding and right.type.display() == "int":
            return {"step_binding": right.id, "step_name": right.name, "sign": 1 if argument.operator == "+" else -1}
    return {}


def fixed_progress(facts, item, bindings, examples, enabled):
    if len(facts.calls) != 1:
        return
    call, = facts.calls
    current = call.arguments[facts.position]
    relation = argument_relation(current, facts, bindings)
    if "offset" not in relation or not 0 <= relation["offset"] * DIRECTION[facts.comparison] <= 4:
        return
    direction = DIRECTION[facts.comparison]
    op = "+" if direction > 0 else "-"
    counter = Evidence("RECURSIVE_DOMAIN_UNCERTAIN",
                       "The base guard establishes a direction. The recurrence step and input domain still require verification.",
                       facts.guard.condition.span)
    base = Evidence("RECURSIVE_RETURN_DEPENDENCY", "This self-call contributes to the returned value under a scalar base guard.", current.span)
    if relation["offset"] == 0 and "dependencies" in enabled:
        yield Proposal((Edit(current.span, f"{facts.parameter} {op} 1"),), "RECURSIVE_DEPENDENCY_PROGRESS", (base,),
                       "Advance the unchanged guarded argument one unit while retaining the surrounding calculation.",
                       "FunctionCall", "arguments", type_match=True, counter_evidence=(counter,))
    guided = {example.args for example in examples
              if not PREDICATES[facts.comparison](example.args[facts.position], facts.threshold)}
    if "nonunit" not in enabled or len(guided) < 2:
        return
    support = Evidence("MULTIPLE_RECURSIVE_EXAMPLES", "Supplied examples enter the recursive path at multiple inputs.", facts.guard.condition.span)
    candidates = []
    # An unchanged, positively sampled scalar parameter can express a variable step.
    for position, parameter in enumerate(item.function.parameters):
        if position == facts.position or parameter.type_name != "int":
            continue
        binding = bindings.declaration(parameter)
        mapped = atom(call.arguments[position], bindings)
        values = {row[position] for row in guided}
        if mapped and mapped[0] == binding and mapped[2] == 0 and len(values) >= 2 and all(1 <= v <= 8 for v in values):
            candidates.append(f"{facts.parameter} {op} {parameter.name}")
    if len(candidates) != 1:
        candidates.clear()
    for step in (1, 2, 3, 4):
        if (step > 1 or relation["offset"] != 0) and step != abs(relation["offset"]):
            candidates.append(f"{facts.parameter} {op} {step}")
    for replacement in candidates[:3]:
        yield Proposal((Edit(current.span, replacement),), "NONUNIT_RECURSIVE_PROGRESS", (base, support),
                       "Compare this bounded progress step against the supplied expectations.",
                       "FunctionCall", "arguments", type_match=True, counter_evidence=(counter,))


def term_combination(context, item, facts, bindings, helpers, examples):
    if len(facts.calls) != 2 or not any(
            not PREDICATES[facts.comparison](example.args[facts.position], facts.threshold) for example in examples):
        return
    flow = item.flow
    expression, site = unalias(facts.value, facts.site, flow, bindings, helpers)
    if not isinstance(expression, ast.BinaryExpression) or expression.operator not in {"+", "-", "*"}:
        return
    terms = []
    for operand in (expression.left, expression.right):
        term, term_site = unalias(operand, site, flow, bindings, helpers)
        if isinstance(term, ast.BinaryExpression) and term.operator == "*":
            for coefficient, value in ((term.left, term.right), (term.right, term.left)):
                if isinstance(coefficient, ast.Literal) and type(coefficient.value) is int and 1 <= coefficient.value <= 4:
                    term, _ = unalias(value, term_site, flow, bindings, helpers)
                    break
        terms.append(term)
    if {id(term) for term in terms} != {id(call) for call in facts.calls}:
        return
    offsets = [argument_relation(call.arguments[facts.position], facts, bindings).get("offset") for call in facts.calls]
    if any(offset is None or not 1 <= offset*DIRECTION[facts.comparison] <= 4 for offset in offsets) or offsets[0] == offsets[1]:
        return
    # Existing profiles already cover two directly combined self-calls.
    if expression is facts.value and terms[0] is expression.left and terms[1] is expression.right:
        return
    operator = next((token for token in context.parsed.tokens
                     if expression.left.span.end.offset <= token.span.start.offset < expression.right.span.start.offset
                     and token.lexeme == expression.operator), None)
    if operator is None:
        return
    for alternate in ("+", "-", "*"):
        if alternate != expression.operator:
            yield Proposal((Edit(operator.span, alternate),), "RECURSIVE_TERM_COMBINATION",
                           (Evidence("LEXICAL_RECURSIVE_TERMS", "Distinct recursive results reach this operator through unique local definitions.", expression.span),),
                           "Compare this operator on the two recursive terms using the supplied expectations.",
                           "BinaryExpression", "operator", type_match=True,
                           counter_evidence=(Evidence("INTENTIONAL_COMBINATION", "The original arithmetic can describe a valid recurrence.", operator.span),))


def helper_argument(item, bindings, helpers, examples):
    if not examples:
        return
    body = item.function.body.statements
    if len(body) != 1 or not isinstance(body[0], ast.ReturnStatement):
        return
    value = body[0].value
    if not isinstance(value, ast.BinaryExpression) or value.operator not in {"+", "*"}:
        return
    left, right = value.left, value.right
    if (not isinstance(left, ast.FunctionCall) or not isinstance(right, ast.FunctionCall)
            or not isinstance(left.callee, ast.Identifier) or not isinstance(right.callee, ast.Identifier)
            or left.callee.name != right.callee.name or left.callee.name not in helpers):
        return
    params = {bindings.declaration(p): i for i, p in enumerate(item.function.parameters)}
    arguments = [[lexical_binding(node, bindings) for node in call.arguments] for call in (left, right)]
    if any(symbol is None or symbol.id not in params for row in arguments for symbol in row):
        return
    used = {symbol.id for row in arguments for symbol in row}
    unused = set(params) - used
    if len(unused) != 1:
        return
    missing, = unused
    index = params[missing]
    distinct = {}
    for example in examples:
        fixed = example.args[:index]+example.args[index+1:]
        if fixed in distinct:
            other = distinct[fixed]
            if other.args[index] != example.args[index] and other.expected_return != example.expected_return:
                break
        else:
            distinct[fixed] = example
    else:
        return
    witness = helpers[left.callee.name]
    same = [i for i in witness["parameter_inputs"] if arguments[0][i].id == arguments[1][i].id]
    if len(same) != 1 or all(a.id == b.id for a, b in zip(*arguments, strict=True)):
        return
    position, = same
    replacement = item.function.parameters[index]
    if arguments[0][position].type.display() != replacement.type_name:
        return
    for call in (left, right):
        argument = call.arguments[position]
        yield Proposal((Edit(argument.span, replacement.name),), "HELPER_ARGUMENT_DEPENDENCY",
                       (Evidence("MISSING_INPUT_DEPENDENCY", "Two supplied expectations differ when only this unused parameter changes.", replacement.span),
                        Evidence("REPEATED_HELPER_ARGUMENT", "Both helper calls use the same lexical value in a contributing parameter.", argument.span)),
                       "Try passing the missing caller parameter at this helper call.",
                       "FunctionCall", "arguments", type_match=True,
                       counter_evidence=(Evidence("AMBIGUOUS_CALL_SITE", "Either helper call could be the intended consumer.", value.span),))


def radix_updates(item, path, bindings, examples, deadline):
    if not examples:
        return
    live = [block for block in item.flow.graph.blocks if path.incoming[block.id]]
    modeled_statements = {id(block.syntax) for block in live}
    for block in live:
        if monotonic() >= deadline:
            return
        loop = block.syntax
        if block.kind != "loop_header" or not isinstance(loop, ast.WhileStatement) or not isinstance(loop.body, ast.Block):
            continue
        expressions = [statement.expression for statement in loop.body.statements
                       if isinstance(statement, ast.ExpressionStatement) and id(statement) in modeled_statements]
        for update in expressions:
            if monotonic() >= deadline:
                return
            if not isinstance(update, ast.Assignment) or update.operator not in {"=", "/="}:
                continue
            target = lexical_binding(update.target, bindings)
            if target is None or target.id in bindings.globals or target.type.display() != "int":
                continue
            if update.operator == "=":
                divide = update.value
                left = lexical_binding(divide.left, bindings) if isinstance(divide, ast.BinaryExpression) else None
                if not left or left.id != target.id or divide.operator != "/":
                    continue
                divisor = divide.right
            else:
                divisor = update.value
            if not isinstance(divisor, ast.Literal) or type(divisor.value) is not int or not 2 <= divisor.value <= 128:
                continue
            other_writes = [node for node in descendants(loop.body) if isinstance(node, (ast.Assignment, ast.UpdateExpression))
                            and lexical_binding(node.target if isinstance(node, ast.Assignment) else node.operand, bindings) == target]
            if len(other_writes) != 1 or any(isinstance(node, ast.FunctionCall) for node in descendants(loop.body)):
                continue
            evidence = {}
            for expression in expressions:
                for node in descendants(expression):
                    if not isinstance(node, ast.BinaryExpression) or node.operator != "%":
                        continue
                    left = lexical_binding(node.left, bindings)
                    if left and left.id == target.id and isinstance(node.right, ast.Literal) and type(node.right.value) is int:
                        evidence[node.right.value] = node.right.span
            condition = loop.condition
            threshold = lexical_binding(condition.left, bindings) if isinstance(condition, ast.BinaryExpression) else None
            if threshold and threshold.id == target.id and condition.operator == ">=" and isinstance(condition.right, ast.Literal):
                for expression in expressions:
                    if (isinstance(expression, ast.Assignment) and expression.operator == "*="
                            and (scale := lexical_binding(expression.target, bindings)) is not None
                            and scale.id != target.id and scale.id not in bindings.globals
                            and isinstance(expression.value, ast.Literal) and type(expression.value.value) is int
                            and expression.value.value == condition.right.value):
                        evidence[expression.value.value] = expression.value.span
            if len(evidence) != 1:
                continue
            radix, = evidence
            if radix == divisor.value or not 2 <= radix <= 36:
                continue
            yield Proposal((Edit(divisor.span, str(radix)),), "RADIX_PROGRESS_MISMATCH",
                           (Evidence("INCONSISTENT_LOOP_RADIX", "The quotient update uses a different radix from the loop's digit extraction or scale.", evidence[radix]),),
                           "Compare a quotient update using the related radix against supplied tests.",
                           "BinaryExpression", "right", type_match=True,
                           counter_evidence=(Evidence("MIXED_RADIX_POSSIBLE", "Programs can intentionally use different radices.", divisor.span),))


def study(context, item, bindings, path, helpers, examples, enabled, deadline):
    selected = selected_examples(item.function, examples)
    facts = recurrence(context, item, bindings, path, helpers, deadline)
    proposals = []
    progress = None
    if facts:
        progress = {"parameter": facts.parameter, "position": facts.position, "comparison": facts.comparison,
                    "threshold": facts.threshold, "direction": DIRECTION[facts.comparison], "complete": True,
                    "calls": [{"span": call.span.to_dict(), "argument": argument_relation(call.arguments[facts.position], facts, bindings),
                               "feeds_return": True} for call in facts.calls]}
        proposals.extend(fixed_progress(facts, item, bindings, selected, enabled))
        if "dependencies" in enabled:
            proposals.extend(term_combination(context, item, facts, bindings, helpers, selected))
    if "dependencies" in enabled and len(proposals) < MAX_NEW and monotonic() < deadline:
        proposals.extend(helper_argument(item, bindings, helpers, selected))
        proposals.extend(islice(radix_updates(item, path, bindings, selected, deadline), max(0, MAX_NEW-len(proposals))))
    return progress, proposals[:MAX_NEW]
