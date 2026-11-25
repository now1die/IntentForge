"""Opt-in semantic-state evidence and bounded source-local repairs."""
from time import monotonic

from analysis_evidence.semantic_state import binding, comparison, propagate, scalar, target_slot
from compiler import ast_nodes as ast

from .intention_phase13 import aggregate_trials, entry_trials
from .intention_candidates import Edit, Evidence, Proposal
from .intention_context import ast_children
from .intention_phase10 import MAX_PROPOSALS, MAX_TRIALS
from .intention_phase10_flow import walk
from .intention_phase105 import Trial
from .intention_phase11 import accepted, sample
from .intention_phase11_flow import RelationalProjection
from .intention_phase8 import ProjectionLimit, UnsupportedProjection
from .intention_phase115 import BASE_PROJECTION

LOGICAL = "LOGICAL_EMPTY_CONSTRAINT"
INITIALIZATION = "SENTINEL_PRESENCE_CONSTRAINT"
COORDINATE = "INDEPENDENT_COORDINATE_CONSTRAINT"
CATEGORIES = frozenset({LOGICAL, INITIALIZATION, COORDINATE})
COMPONENTS = frozenset({"logical", "initialization", "coordinate"})
MAX_FACTS = 48


def binary(node, operator):
    return isinstance(node, ast.BinaryExpression) and node.operator == operator


def fact(kind, item, block, key, **details):
    return {"kind": kind, "function": item.function.name, "span": (block.expression or block.syntax).span.to_dict(),
            "binding": key, "cfg_site": block.id, "basis": "STATIC", **details}


def state_evidence(item, block, state, index, arrays):
    if block.expression is None:
        return
    seen = set()
    writes = item.flow.effects[block.id].writes
    pending = [block.expression]
    while pending:
        node = pending.pop()
        if isinstance(node, ast.Assignment) and node.operator == "=":
            pending.append(node.value)
            if isinstance(node.target, ast.ArrayAccess):
                pending.append(node.target.index)
            continue
        if isinstance(node, ast.ArrayAccess) and (key := binding(index, node.array)) in arrays:
            position = scalar(node.index)
            validity = "UNKNOWN"
            if type(position) is int:
                validity = "VALID" if 0 <= position < arrays[key] else "INVALID"
            yield fact("physical_index", item, block, key, span=node.span.to_dict(),
                       name=index.symbols[key].name, cell=position, physical_extent=arrays[key],
                       validity=validity, assumptions=["Physical address validity is independent of logical activity."])
        slot = target_slot(index, node, arrays)
        if slot and slot not in seen and slot[0] not in index.globals:
            seen.add(slot)
            if slot[0] in writes or slot[1] is None and slot[0] in arrays:
                continue
            key, cell = slot
            yield fact("initialization", item, block, key, span=node.span.to_dict(),
                       name=index.symbols[key].name, cell=cell, initialization=state.initialization(slot),
                       value=next((value for place, _, value in state.constants if place == slot), None),
                       presence="UNKNOWN",
                       definitions=[definition.site for definition in item.flow.for_binding(block.id, key)],
                       assumptions=[list(path[1:]) for path in sorted(state.paths) if path[0] == key])
        pending.extend(child for _, child in reversed(tuple(ast_children(node))))


def unit_increment(index, node, induction):
    if isinstance(node, ast.UpdateExpression):
        return node.operator == "++" and binding(index, node.operand) == induction
    if not isinstance(node, ast.Assignment) or binding(index, node.target) != induction:
        return False
    if node.operator == "+=":
        return scalar(node.value) == 1
    return (node.operator == "=" and binary(node.value, "+")
            and binding(index, node.value.left) == induction and scalar(node.value.right) == 1)


def loop_prefixes(item, index, arrays):
    """Identify source-local prefix scans over explicit entry length bindings."""
    parameter_ids = {index.declaration(node): i for i, node in enumerate(item.function.parameters)
                     if node.type_name == "int"}
    for block in item.flow.graph.blocks:
        loop = block.syntax
        if block.kind != "loop_header" or not isinstance(loop, ast.ForStatement):
            continue
        if binary(loop.condition, "<"):
            induction_node, limit = loop.condition.left, loop.condition.right
        elif binary(loop.condition, ">"):
            induction_node, limit = loop.condition.right, loop.condition.left
        else:
            continue
        start = loop.initializer
        if not isinstance(start, ast.VariableDeclaration) or scalar(start.initializer) not in {0, 1}:
            continue
        induction, length = binding(index, induction_node), binding(index, limit)
        if induction != index.declaration(start) or length not in parameter_ids:
            continue
        if not unit_increment(index, loop.update, induction):
            continue
        body = [site for site in item.flow.graph.blocks if loop.body.span.start.offset <= site.syntax.span.start.offset
                and site.syntax.span.end.offset <= loop.body.span.end.offset]
        if any(item.flow.effects[site.id].writes & {induction, length} for site in body):
            continue
        if any(definition.site != item.flow.graph.entry for definition in item.flow.for_binding(block.id, length)):
            continue
        keys = {binding(index, node.array) for node in walk(loop.body)
                if isinstance(node, ast.ArrayAccess) and binding(index, node.index) == induction}
        for key in sorted(keys & arrays.keys()):
            yield block, key, length, parameter_ids[length]


def logical_analysis(item, states, index, arrays, spec, forms):
    for block, array, length, position in loop_prefixes(item, index, arrays):
        size = arrays[array]
        observations = [{"input": i, "logical_length": row.args[position], "active_interval": [0, row.args[position]],
                         "inactive_interval": [row.args[position], size]}
                        for i, row in enumerate(spec.examples, 1) if type(row.args[position]) is int
                        and 0 <= row.args[position] <= size]
        forms.append(fact("logical_array", item, block, array, name=index.symbols[array].name,
                          physical_extent=size, logical_length=index.symbols[length].name, length_binding=length,
                          active_interval=f"[0, {index.symbols[length].name})",
                          assumptions=["The loop bound describes the active prefix when length lies within capacity."],
                          observations=observations if len(observations) == len(spec.examples) else []))
        # A known-empty path has no logically active cell, even if an
        # alternative offset would make that physical address valid.
        for site in item.flow.graph.blocks:
            if site.kind != "return" or site.id not in states:
                continue
            value = site.expression
            empty_paths = [path for path in states[site.id].paths if path[:3] == (length, "==", 0)]
            if not empty_paths or any(definition.site != item.flow.graph.entry
                                      for definition in item.flow.for_binding(site.id, length)):
                continue
            effect = item.flow.effects[site.id]
            if not (isinstance(value, ast.ArrayAccess) and binding(index, value.array) == array
                    and not (effect.writes or effect.calls)):
                continue
            forms.append(fact("inactive_read", item, site, array, name=index.symbols[array].name,
                              physical_extent=size, logical_length=0, active_interval="[0, 0)",
                              assumptions=[list(path[1:]) for path in sorted(empty_paths)]))
            empty = [row.expected_return for row in spec.examples if row.args[position] == 0]
            if not observations or len(observations) != len(spec.examples) or len(observations) <= len(empty):
                continue
            if empty and all(type(other) is type(empty[0]) and other == empty[0] for other in empty):
                result = str(empty[0]).lower()
                yield Trial(LOGICAL, (Edit(value.span, result),),
                            "The proven empty branch has no active cell. Supplied empty examples specify its result.")


def rejection_return(node):
    """Unwrap returns behind nested scopes with only inert literal declarations."""
    while isinstance(node, ast.Block):
        if not node.statements:
            return None
        for prefix in node.statements[:-1]:
            if not isinstance(prefix, ast.Block) or any(
                not isinstance(part, (ast.Block, ast.Literal)) and
                not (isinstance(part, ast.VariableDeclaration) and isinstance(part.initializer, ast.Literal))
                for part in walk(prefix)
            ):
                return None
        node = node.statements[-1]
    return node if isinstance(node, ast.ReturnStatement) else None


def coordinates(context, item, states, index, arrays, spec, forms):
    params = {index.declaration(param): pos for pos, param in enumerate(item.function.parameters)
              if param.type_name == "int"}
    for site in item.flow.graph.blocks:
        cell = site.expression
        if site.kind != "return" or not isinstance(cell, ast.ArrayAccess) or site.id not in states:
            continue
        key, address = binding(index, cell.array), cell.index
        if key not in arrays or not binary(address, "+") or not binary(address.left, "*"):
            continue
        row, col = binding(index, address.left.left), binding(index, address.right)
        width = scalar(address.left.right)
        if row not in params or col not in params or row == col or type(width) is not int or not 0 < width <= arrays[key]:
            continue
        height, remainder = divmod(arrays[key], width)
        if remainder or any(definition.site != item.flow.graph.entry for coordinate in (row, col)
                            for definition in item.flow.for_binding(site.id, coordinate)):
            continue
        axes = ((row, height), (col, width))
        paths = states[site.id].paths
        for coordinate, bound in axes:
            checks = {(operator, value) for name, operator, value, _, _ in paths if name == coordinate}
            forms.append(fact("coordinate", item, site, coordinate, name=index.symbols[coordinate].name,
                              axis="row" if coordinate == row else "column", lower=0, upper_exclusive=bound,
                              validity=("VALID" if {(">=", 0), ("<", bound)} <= checks else "INVALID"
                                        if checks & {("<", 0), (">=", bound)} else "UNKNOWN"),
                              coordinate_observations=[{"input": i, "value": entry.args[params[coordinate]],
                                  "validity": "VALID" if 0 <= entry.args[params[coordinate]] < bound else "INVALID"}
                                  for i, entry in enumerate(spec.examples, 1)],
                              assumptions=[list(path[1:]) for path in sorted(paths) if path[0] == coordinate]))
        # Reuse the result of an existing single-axis rejection whose
        # fallthrough dominates the read. Require observed rejected values
        # for the other axis while the established axis is in range.
        for checked, bound in axes:
            missing, limit = (col, width) if checked == row else (row, height)
            low_sites = {path[3] for path in paths if path[:3] == (checked, ">=", 0) and path[4] == "false"}
            high_sites = {path[3] for path in paths if path[:3] == (checked, "<", bound) and path[4] == "false"}
            for guard in sorted(low_sites & high_sites):
                block = item.flow.graph.blocks[guard]
                branch = block.syntax
                if not isinstance(branch, ast.IfStatement) or branch.else_branch is not None:
                    continue
                rejection = rejection_return(branch.then_branch)
                expected = scalar(rejection.value) if rejection else None
                if expected is None or not binary(branch.condition, "||"):
                    continue
                checks = {comparison(index, part) for part in (branch.condition.left, branch.condition.right)}
                if checks != {(checked, "<", 0), (checked, ">=", bound)}:
                    continue
                outside = [entry.args[params[missing]] for entry in spec.examples
                           if 0 <= entry.args[params[checked]] < bound and entry.expected_return == expected]
                if not (any(value < 0 for value in outside) and any(value >= limit for value in outside)
                        and any(0 <= entry.args[params[row]] < height and 0 <= entry.args[params[col]] < width
                                for entry in spec.examples)):
                    continue
                name = index.symbols[missing].name
                visible = context.visible_at(branch.condition.span.start.offset).get(name)
                if visible is None or visible.id != missing or any(definition.site != item.flow.graph.entry
                                          for definition in item.flow.for_binding(block.id, missing)):
                    continue
                original = context.text(branch.condition.span)
                yield Trial(COORDINATE, (Edit(branch.condition.span,
                            f"{original} || {name} < 0 || {name} >= {limit}"),),
                            "The guarded row-major read requires independent signed bounds on both coordinates.")


def direct_assignment(node):
    if isinstance(node, ast.ExpressionStatement) and isinstance(node.expression, ast.Assignment):
        assignment = node.expression
        if assignment.operator == "=":
            return assignment
    return None


def presence_flags(item, index, value, block):
    """Recognize the closed false -> true flag protocol in one lexical block."""
    statements = item.function.body.statements
    if block.syntax not in statements:
        return
    before = statements[:statements.index(block.syntax)]
    for declaration in before:
        if not isinstance(declaration, ast.VariableDeclaration) or scalar(declaration.initializer) is not False:
            continue
        flag = index.declaration(declaration)
        for transition in before[before.index(declaration) + 1:]:
            if not (isinstance(transition, ast.IfStatement) and transition.else_branch is None
                    and isinstance(transition.then_branch, ast.Block)):
                continue
            updates = [direct_assignment(node) for node in transition.then_branch.statements]
            if len(updates) != 2 or any(node is None for node in updates):
                continue
            data, present = updates
            if (binding(index, data.target), binding(index, present.target), scalar(present.value)) != (value, flag, True):
                continue
            expected = {id(declaration), id(transition.then_branch.statements[0]),
                        id(transition.then_branch.statements[1])}
            all_writes = [site for site in item.flow.graph.blocks
                          if item.flow.effects[site.id].writes & {flag, value}
                          and site.syntax.span.start.offset < block.syntax.span.start.offset]
            value_decl = [site for site in all_writes if isinstance(site.syntax, ast.VariableDeclaration)
                          and index.declaration(site.syntax) == value]
            if len(value_decl) == 1 and value_decl[0].syntax in before[:before.index(transition)] and {
                    id(site.syntax) for site in all_writes} == expected | {id(value_decl[0].syntax)}:
                yield index.symbols[flag].name, flag, data.span


def sentinel_analysis(item, states, index, forms):
    for block in item.flow.graph.blocks:
        test = comparison(index, block.expression)
        if block.kind != "branch" or test is None or block.id not in states:
            continue
        key, op, marker = test
        if op not in {"==", "!="} or marker >= 0:
            continue
        definitions = item.flow.for_binding(block.id, key)
        reaching = [item.flow.graph.blocks[definition.site].expression for definition in definitions]
        defaults = [node for node in reaching if isinstance(node, ast.VariableDeclaration)
                    and scalar(node.initializer) == marker]
        assignments = [node.expression for node in reaching if isinstance(node, ast.ExpressionStatement)
                       and isinstance(node.expression, ast.Assignment)
                       and binding(index, node.expression.target) == key]
        if not defaults or not assignments:
            continue
        collision = "POSSIBLE" if any(scalar(node.value) in {None, marker} for node in assignments) else "UNESTABLISHED"
        forms.append(fact("sentinel", item, block, key, name=index.symbols[key].name, marker=marker,
                          initialization=states[block.id].initialization((key, None)), presence="UNKNOWN",
                          collision=collision, definitions=[definition.site for definition in definitions],
                          assumptions=["A numeric test alone establishes no presence contract."]))
        if collision != "POSSIBLE":
            continue
        for name, flag, assignment_span in presence_flags(item, index, key, block):
            forms.append(fact("presence", item, block, flag, name=name, presence="FLAG_GUARDED",
                              assumptions=["The existing flag is set on the same branch as the data write."],
                              transition_span=assignment_span.to_dict()))
            yield Trial(INITIALIZATION, (Edit(block.expression.span, f"!{name}" if op == "==" else name),),
                        "The existing Boolean flag records the presence transition independently of its numeric value.")


def synthesize(context, program, spec, enabled, inherited):
    report = {"status": program.status, "components": sorted(enabled), "facts": [], "trials": 0,
              "compatible_candidates": 0, "withheld": []}
    if program.status != "AVAILABLE":
        return inherited, report
    trials, contracts, reads = [], [], []
    selected = spec.function
    for item in program.functions:
        states, arrays = propagate(item, program.bindings, program.deadline)
        if states is None:
            return inherited, report | {"status": "ANALYSIS_LIMITED", "facts": []}
        for block in item.flow.graph.blocks:
            if block.id in states and len(reads) < MAX_FACTS:
                reads.extend(state_evidence(item, block, states[block.id], program.bindings, arrays))
        if selected and item.function.name != selected:
            continue
        if "initialization" in enabled:
            trials.extend(sentinel_analysis(item, states, program.bindings, contracts))
        if "entry" in enabled and selected and item.function.body.statements:
            trials.extend(entry_trials(item, program.bindings, arrays, spec))
            trials.extend(aggregate_trials(item, program.bindings, arrays))
        if "logical" in enabled:
            trials.extend(logical_analysis(item, states, program.bindings, arrays, spec, contracts))
        if "coordinate" in enabled:
            trials.extend(coordinates(context, item, states, program.bindings, arrays, spec, contracts))
    report["facts"] = (contracts + reads)[:MAX_FACTS]
    protected = [(row["span"]["start"]["offset"], row["span"]["end"]["offset"])
                 for row in contracts if row["kind"] == "inactive_read"]
    compatible = []
    for proposal in inherited:
        if any(start <= edit.span.start.offset < end or edit.span.start.offset < start < edit.span.end.offset
               for edit in proposal.edits for start, end in protected):
            if len(report["withheld"]) < MAX_FACTS:
                report["withheld"].append({"category": proposal.category,
                                           "reason": "This edit changes an empty-branch read. A physical offset cannot establish a logical value."})
        else:
            compatible.append(proposal)
    generated = []
    if trials and len({row.args for row in spec.examples}) >= 3:
        try:
            model = RelationalProjection(context, program, BASE_PROJECTION)
            model.compile(spec.function)
            originals = sample(model, spec)
        except UnsupportedProjection:
            return tuple(compatible), report | {"status": "UNSUPPORTED_PROJECTION"}
        except ProjectionLimit:
            return tuple(compatible), report | {"status": "ANALYSIS_LIMITED"}
        if all(type(result.value) is type(row.expected_return) and result.value == row.expected_return
               for (result, _), row in zip(originals, spec.examples, strict=True)):
            return tuple(compatible), report | {"status": "CONSTRAINTS_ALREADY_AGREE"}
    for trial in list(dict.fromkeys(trials))[:MAX_TRIALS]:
        if len({row.args for row in spec.examples}) < 3 or monotonic() >= program.deadline:
            break
        report["trials"] += 1
        if not accepted(context, program, spec, trial, BASE_PROJECTION):
            continue
        report["compatible_candidates"] += 1
        if len(generated) < MAX_PROPOSALS:
            span = trial.edits[0].span
            generated.append(Proposal(trial.edits, trial.category,
                             (Evidence("FINITE_CONSTRAINT_WITNESS", trial.basis, span),),
                             "Review the source diff and the limits of the sampled evidence.",
                             "ControlFlow", "semantic_state", type_match=True, counter_evidence=(
                                 Evidence("FINITE_DOMAIN", "Only supplied expectations were checked during synthesis.", span),)))
    report["status"] = ("ANALYSIS_LIMITED" if monotonic() >= program.deadline else
                        "MULTIPLE_COMPATIBLE_EDITS" if report["compatible_candidates"] > 1 else
                        "COMPATIBLE_EDIT" if generated else
                        "INCOMPLETE_SPECIFICATION" if not spec.examples else "OBSERVATION_ONLY")
    return (*generated, *compatible), report
