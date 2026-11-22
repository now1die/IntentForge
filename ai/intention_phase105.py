"""Generate bounded repairs from checked endpoint and relational evidence."""
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from time import monotonic

from analysis_evidence.function_summary import analyze_program
from compiler import ast_nodes as ast
from compiler.source_location import SourceSpan

from .intention_candidates import Edit, Evidence, Proposal, apply_edits, point
from .intention_context import build_context
from .intention_phase8 import ProjectionLimit, UnsupportedProjection, edit_cost
from .intention_phase10 import MAX_PROPOSALS, MAX_TRIALS
from .intention_phase10_flow import assignment, literal, walk
from .intention_phase95_flow import project
from .intention_phase105_flow import EndpointProgress, EndpointProjection

ENDPOINT = "ENDPOINT_SEARCH_CONSTRAINT"
NEIGHBOR = "ADJACENT_CELL_CONSTRAINT"
ROTATION = "ROTATION_INTERVAL_CONSTRAINT"
ZERO = "CHECKED_ZERO_GUARD"
AGGREGATE = "DERIVED_AGGREGATE_CONSTRAINT"
COMPONENTS = frozenset({"endpoint","neighbor","rotation","zero","aggregate"})
CATEGORIES = frozenset({ENDPOINT,NEIGHBOR,ROTATION,ZERO,AGGREGATE})
REVERSED = {"<":">",">":"<","<=":">=",">=":"<="}
STRICT = {"<":"<=",">":">=","<=":"<",">=":">"}


@dataclass(frozen=True,slots=True)
class Trial:
    category: str
    edits: tuple[Edit,...]
    basis: str


def returned(branch):
    if isinstance(branch,ast.Block) and len(branch.statements)==1:
        branch = branch.statements[0]
    return branch if isinstance(branch,ast.ReturnStatement) else None


def observations(relation,samples):
    return [witness.relations.get(id(relation.node),()) for _,witness in samples]


def inspect_samples(model,spec):
    samples = []
    for example in spec.examples:
        observer = EndpointProgress(model)
        result = project(model,spec.function,example.args,observer=observer,inspect=observer.inspection)
        observer.inspection.accesses = observer.accesses
        samples.append((result,observer.inspection))
    return samples


def key_contracts(relation,samples,spec):
    possible = {"first_equal","last_equal","lower_bound","upper_bound","saturated_lower","saturated_upper"}
    pairs, duplicates = 0,0
    sentinels = {example.expected_return for example in spec.examples if type(example.expected_return) is int
                 and example.expected_return<0}
    sentinel = next(iter(sentinels)) if len(sentinels)==1 else None
    for rows,example in zip(observations(relation,samples),spec.examples,strict=True):
        if not rows:
            continue
        cells,key = rows[0][3],rows[0][5]
        if not cells or None in cells or tuple(sorted(cells))!=cells or type(example.expected_return) is not int:
            return (),0,0
        # A scan may rewrite a local array. Endpoint classification requires
        # the observed key and ordered cells to agree within each sample.
        if any(row[3]!=cells or row[5]!=key for row in rows):
            return (),0,0
        low,high=bisect_left(cells,key),bisect_right(cells,key)
        pairs+=1
        duplicates+=high-low>1
        expected = {"first_equal":low if low<high else sentinel,"last_equal":high-1 if low<high else sentinel,
                    "lower_bound":low,"upper_bound":high,"saturated_lower":min(low,len(cells)-1),
                    "saturated_upper":min(high,len(cells)-1)}
        possible &= {kind for kind,value in expected.items() if value==example.expected_return}
    return tuple(sorted(possible)) if pairs>=3 else (),pairs,duplicates


def endpoint_trials(model,samples,spec,evidence):
    for name in model.models:
        function = model.functions[name].function
        recursive = model.recursive.get(name)
        for scope in walk(function.body):
            statements = scope.statements if isinstance(scope,ast.Block) else []
            for i,early in enumerate(statements):
                if not isinstance(early,ast.IfStatement):
                    continue
                relation = model.relations.get(id(early.condition))
                if relation is None or relation.kind!="key" or early.condition.operator!="==":
                    continue
                hit = returned(early.then_branch)
                cell = early.condition.left if relation.cell_on_left else early.condition.right
                key = early.condition.right if relation.cell_on_left else early.condition.left
                mid = model.index(cell.index)
                if not hit or model.index(hit.value)!=mid:
                    continue
                contracts,n,duplicates = key_contracts(relation,samples,spec)
                if not contracts:
                    continue
                evidence.append({"kind":"endpoint","function":name,"span":early.condition.span.to_dict(),
                                 "contracts":list(contracts),"samples":n,"duplicate_samples":duplicates,
                                 "extent":model.array_info(cell)[1],
                                 "termination":"endpoint collapse" if recursive and not recursive.inclusive else "key match"})
                if not duplicates:
                    continue
                refine = early.else_branch if early.else_branch else statements[i+1] if i+1<len(statements) else None
                if recursive and not recursive.inclusive:
                    yield from recursive_refinement(model,recursive,early,refine,relation,contracts)
                elif any(interval.midpoint==mid for interval in model.intervals.get(name,())):
                    yield from equal_refinement(model,function,early,cell,key,contracts)


def endpoint_observations(model,samples,spec,evidence):
    recorded = set()
    for name,intervals in model.intervals.items():
        for interval in intervals:
            for relation in model.relations.values():
                node = relation.node
                if relation.kind!="key" or node.operator not in STRICT:
                    continue
                cell = node.left if relation.cell_on_left else node.right
                if model.index(cell.index)!=interval.midpoint or interval.span.start.offset>node.span.start.offset:
                    continue
                contracts,n,duplicates = key_contracts(relation,samples,spec)
                if not contracts or name in recorded:
                    continue
                recorded.add(name)
                evidence.append({"kind":"endpoint","function":name,"span":node.span.to_dict(),"contracts":list(contracts),
                                 "samples":n,"duplicate_samples":duplicates,"extent":interval.length,
                                 "termination":"inclusive" if interval.inclusive else "collapse or half-open"})
                break


def recursive_refinement(model,interval,early,refine,relation,contracts):
    if not isinstance(refine,ast.IfStatement):
        return
    test = refine.condition
    other = model.relations.get(id(test))
    if not other or other.kind!="key" or other.array!=relation.array or test.operator not in {"<",">"}:
        return
    first,second = (test.left,test.right) if other.cell_on_left else (test.right,test.left)
    key = relation.node.right if relation.cell_on_left else relation.node.left
    if model.index(first.index)!=interval.midpoint or model.index(second)!=model.index(key):
        return
    direction = REVERSED[test.operator] if other.cell_on_left else test.operator
    branch = returned(refine.then_branch)
    if not branch or not isinstance(branch.value,ast.FunctionCall) or id(branch.value) not in interval.calls:
        return
    low,high = interval.positions
    args = branch.value.arguments
    if direction=="<":
        if model.index(args[low])!=interval.low or model.index(args[high])!=interval.midpoint:
            return
        inclusive_mode,strict_mode = "lower","upper"
    else:
        if model.affine_index(args[low])!=(interval.midpoint,1) or model.index(args[high])!=interval.high:
            return
        inclusive_mode,strict_mode = "upper","lower"
    token = model.operator_span(test)
    if token is None:
        return
    head = SourceSpan(early.span.start,refine.span.start) if early.else_branch else early.span
    for mode in (inclusive_mode,strict_mode):
        if not set(contracts)&{f"{mode}_bound",f"saturated_{mode}"}:
            continue
        edits = (Edit(head,""),)
        if mode==inclusive_mode:
            edits += (Edit(token,STRICT[test.operator]),)
        yield Trial(ENDPOINT,edits,f"The sampled {mode}-endpoint contract requires refining the interval on equality.")


def equal_refinement(model,function,early,cell,key,contracts):
    midpoint = model.index(cell.index)
    interval = next((row for row in model.intervals[function.name] if row.midpoint==midpoint and not row.positions),None)
    if interval is None or function.body.statements[-1].span.start.offset<=early.span.end.offset:
        return
    extent = model.array_info(cell)[1]
    endpoints = {model.bindings.declaration(node):node.initializer for node in function.body.statements
                 if isinstance(node,ast.VariableDeclaration) and node.span.start.offset<interval.span.start.offset}
    if not (literal(endpoints.get(interval.low),0) and literal(endpoints.get(interval.high),extent-int(interval.inclusive))):
        return
    i,array,wanted = (model.context.text(node.span) for node in (cell.index,cell.array,key))
    for kind,direction in (("first_equal",-1),("last_equal",1)):
        if kind not in contracts:
            continue
        op,limit,delta,step = (">",0,"-","--") if direction<0 else ("<",extent-1,"+","++")
        replacement = f"{{ while ({i} {op} {limit} && {array}[{i} {delta} 1] == {wanted}) {{ {i}{step}; }} return {i}; }}"
        yield Trial(ENDPOINT,(Edit(early.then_branch.span,replacement),),
                    f"Trusted duplicate examples support {kind.replace('_',' ')} across checked neighbors.")


def rotation_shape(model,relation):
    node = relation.node
    interval = next((interval for intervals in model.intervals.values() for interval in intervals
                     if {model.index(part.index) for part in (node.left,node.right)}=={interval.midpoint,interval.high}),None)
    if interval is None:
        return None
    declarations = {model.bindings.declaration(part):part.initializer for part in model.nodes.values()
                    if isinstance(part,ast.VariableDeclaration)}
    if not (literal(declarations.get(interval.low),0) and literal(declarations.get(interval.high),interval.length-1)):
        return None
    branch = next((part for part in model.nodes.values() if isinstance(part,ast.IfStatement)
                   and part.condition is node and part.else_branch),None)
    if branch is None:
        return None

    def update(body):
        if isinstance(body,ast.Block) and len(body.statements)==1:
            body = body.statements[0]
        node = assignment(body)
        return node if isinstance(node,ast.Assignment) and node.operator=="=" else None

    first,second = update(branch.then_branch),update(branch.else_branch)
    if first is None or second is None:
        return None
    goes_right = model.index(first.target)==interval.low
    lower,upper = (first,second) if goes_right else (second,first)
    if model.index(lower.target)!=interval.low or model.index(upper.target)!=interval.high:
        return None
    if model.index(upper.value)!=interval.midpoint:
        return None
    advance = model.affine_index(lower.value)
    if advance is None or advance[0]!=interval.midpoint or advance[1] not in {0,1}:
        return None
    mid_left = model.index(node.left.index)==interval.midpoint
    wanted = ">" if mid_left==goes_right else "<"
    return interval.length,wanted,lower.value if advance[1]==0 else None


def relation_trials(model,samples,spec,evidence,enabled):
    for relation in model.relations.values():
        if relation.kind not in {"neighbor","rotation"}:
            continue
        rows = observations(relation,samples)
        compared = [value for row in rows for value in row]
        if not compared:
            continue
        node = relation.node
        token = model.operator_span(node)
        if token is None:
            continue
        supporting = [i for i,row in enumerate(rows,1) if row]
        fact = {"kind":relation.kind,"span":node.span.to_dict(),"inputs":supporting,
                "observations":[{"left_index":a,"right_index":b,"left_value":x,"right_value":y}
                                for a,x,y,_,b,_ in compared[:8]]}
        evidence.append(fact)
        if relation.kind=="rotation" and "rotation" in enabled:
            shape = rotation_shape(model,relation)
            extent = shape[0] if shape else None
            checks = []
            for row,example in zip(rows,spec.examples,strict=True):
                if not row or not extent:
                    continue
                cells = row[0][3]
                if None in cells or len(set(cells))!=extent:
                    checks.append(False)
                    continue
                pivot = cells.index(min(cells))
                ordered = cells[pivot:]+cells[:pivot]
                checks.append(tuple(sorted(cells))==ordered and example.expected_return==pivot)
            fact["assumption"]="distinct cells in cyclic increasing order; minimum position expected"
            fact["supported_samples"]=sum(checks)
            if len(checks)>=2 and all(checks) and len(checks)==len(rows):
                _,wanted,latch = shape
                edits = []
                if node.operator not in {wanted,STRICT[wanted]}:
                    edits.append(Edit(token,wanted))
                if latch is not None:
                    midpoint = model.context.text(latch.span)
                    edits.append(Edit(latch.span,f"{midpoint} + 1"))
                if edits:
                    yield Trial(ROTATION,tuple(edits),
                                "Checked cells support a distinctly ordered rotation and a strictly shrinking pivot interval.")
        if relation.kind=="neighbor" and "neighbor" in enabled and len(supporting)>=2 and node.operator in STRICT:
            for op in (STRICT[node.operator],REVERSED[node.operator]):
                yield Trial(NEIGHBOR,(Edit(token,op),),"Checked comparisons establish both adjacent cells on sampled paths.")


def zero_trials(model,samples,spec,evidence):
    function = model.functions[spec.function].function
    failed = [(i,witness.faults[-1]) for i,(result,witness) in enumerate(samples)
              if result.value is None and witness.faults]
    if not failed or any(result.value is None and not witness.faults for result,witness in samples):
        return
    fault_ids = {parts[0] for _,parts in failed}
    if len(fault_ids)!=1 or any(operation not in {"/","%"} or divisor!=0 for _,(_,operation,_,divisor) in failed):
        return
    binary = model.nodes.get(next(iter(fault_ids)))
    function_nodes = {id(node) for node in walk(function.body)}
    if not isinstance(binary,ast.BinaryExpression) or id(binary) not in function_nodes:
        return
    denominator = binary.right
    args = denominator.arguments if isinstance(denominator,ast.FunctionCall) else [denominator]
    if not 1<=len(args)<=2:
        return
    parameter_ids = [model.bindings.declaration(parameter) for parameter in function.parameters]
    dependencies = {model.index(node) for node in args}
    if None in dependencies or not dependencies<=set(parameter_ids):
        return
    positions = [i for i,binding in enumerate(parameter_ids) if binding in dependencies]
    guarded = [example for example in spec.examples if any(example.args[i]==0 for i in positions)]
    expected = {example.expected_return for example in guarded}
    if len(expected)!=1 or not all(any(example.args[i]==0 and all(example.args[j]!=0 for j in positions if j!=i)
                                       for example in guarded) for i in positions):
        return
    if sum(all(example.args[i]!=0 for i in positions) and result.value==example.expected_return
           for example,(result,_) in zip(spec.examples,samples,strict=True))<2:
        return
    opening = next((token for token in model.context.parsed.tokens if token.lexeme=="{"
                    and token.span.start.offset==function.body.span.start.offset),None)
    if not opening:
        return
    value = next(iter(expected))
    value_text = str(value).lower() if type(value) is bool else str(value)
    names = [function.parameters[i].name for i in positions]
    predicate = " || ".join(f"{name} == 0" for name in names)
    detail = {"kind":"zero","span":binary.span.to_dict(),"parameters":names,"expected":value,
              "inputs":[i+1 for i,_ in failed],"guard":predicate}
    evidence.append(detail)
    yield Trial(ZERO,(Edit(point(opening.span.end),f"\n    if ({predicate}) {{ return {value_text}; }}\n"),),
                "Typed zero-input examples specify the return for each selected denominator dependency.")


def aggregate_trials(model,spec,evidence):
    entry = model.functions[spec.function].function
    if not model.digit_sites:
        return
    for name,span in model.digit_sites.items():
        evidence.append({"kind":"helper","function":name,"span":span.to_dict(),
                         "assumption":"both nonnegative helper arguments halve at each entered latch"})
    origins = {}
    for statement in entry.body.statements:
        if not isinstance(statement,ast.ForStatement):
            continue
        loop = statement
        for node in walk(loop.body):
            if not isinstance(node,ast.IfStatement) or not isinstance((cond:=node.condition),ast.BinaryExpression):
                continue
            if cond.operator not in {"<",">"} or not isinstance(cond.left,ast.ArrayAccess) or model.array_info(cond.left) is None:
                continue
            statements = node.then_branch.statements if isinstance(node.then_branch,ast.Block) else [node.then_branch]
            if len(statements)!=1 or not isinstance((update:=assignment(statements[0])),ast.Assignment):
                continue
            binding = model.index(cond.right)
            if (binding and update.operator=="=" and model.index(update.target)==binding
                    and isinstance(update.value,ast.ArrayAccess) and model.array_info(update.value)==model.array_info(cond.left)
                    and model.index(update.value.index)==model.index(cond.left.index)):
                origins[binding]=(loop.span,cond.operator)
        init = loop.initializer
        if not isinstance(init,ast.VariableDeclaration) or not isinstance(init.initializer,ast.Literal):
            continue
        if not any(isinstance(node,ast.FunctionCall) and isinstance(node.callee,ast.Identifier)
                   and node.callee.name in model.digit_sites for node in walk(loop.body)):
            continue
        site = init.initializer.span
        for binding,(span,kind) in origins.items():
            if span.end.offset>site.start.offset or kind!="<":
                continue
            name = model.bindings.symbols[binding].name
            visible = model.context.visible_at(site.start.offset).get(name)
            if visible is None or visible.id!=binding:
                continue
            evidence.append({"kind":"origin","span":site.to_dict(),"origin":name,"scan":span.to_dict()})
            yield Trial(AGGREGATE,(Edit(site,name),),"The aggregate traverses from a reaching minimum over checked array cells.")


def accepted(context,program,spec,trial,digit_helpers):
    source = apply_edits(context.source,trial.edits)
    candidate = build_context(source,None)
    if not candidate.compiler_valid:
        return False
    revised = analyze_program(candidate,program.deadline)
    if revised.status!="AVAILABLE":
        return False
    projection = EndpointProjection(candidate,revised,digit_helpers=digit_helpers)
    try:
        projection.compile(spec.function)
        for example in spec.examples:
            result = project(projection,spec.function,example.args,observer=EndpointProgress(projection,strict=True))
            if type(result.value) is not type(example.expected_return) or result.value!=example.expected_return:
                return False
    except (UnsupportedProjection,ProjectionLimit):
        return False
    return True


def synthesize(context,program,spec,enabled):
    report = {"status":"INCOMPLETE_SPECIFICATION","scope":"SUPPLIED_EXAMPLES_ONLY","components":sorted(enabled),
              "trials":0,"compatible_candidates":0,"facts":[],"witnesses":[]}
    if not enabled or len({row.args for row in spec.examples})<3 or spec.return_type not in {"int","bool"}:
        return (),report
    if program.status!="AVAILABLE" or context.parsed.ast.globals:
        return (),report | {"status":"UNSUPPORTED_PROJECTION"}
    digits = "aggregate" in enabled
    model = EndpointProjection(context,program,digit_helpers=digits)
    try:
        model.compile(spec.function)
        results = inspect_samples(model,spec)
    except UnsupportedProjection:
        return (),report | {"status":"UNSUPPORTED_PROJECTION"}
    except ProjectionLimit:
        return (),report | {"status":"ANALYSIS_LIMITED"}
    report["sample_issues"] = [row.issue for row,_ in results]
    report["arrays"] = sorted(model.arrays.values(),key=lambda row:row["span"]["start"]["offset"])
    report["access_issues"] = [
        {"sample":i,"span":model.sites[site].to_dict(),"status":"INVALID_INDEX" if not cell["valid"] else "MISSING_CELL_FACT"}
        for i,(_,witness) in enumerate(results,1) for site,cell in witness.accesses.items()
        if not cell["valid"] or not cell["initialized"]
    ][:40]
    evidence = report["facts"]
    candidates = []
    if "endpoint" in enabled:
        candidates.extend(endpoint_trials(model,results,spec,evidence))
        if not any(row["kind"]=="endpoint" for row in evidence):
            endpoint_observations(model,results,spec,evidence)
    if enabled & {"neighbor","rotation"}:
        candidates.extend(relation_trials(model,results,spec,evidence,enabled))
    if "zero" in enabled:
        candidates.extend(zero_trials(model,results,spec,evidence))
    if digits:
        candidates.extend(aggregate_trials(model,spec,evidence))
    del evidence[64:]
    if all(type(row.value) is type(example.expected_return) and row.value==example.expected_return
           for (row,_),example in zip(results,spec.examples,strict=True)):
        return (),report | {"status":"CONSTRAINTS_ALREADY_AGREE"}
    ordered = sorted(set(candidates),key=lambda trial:(len(trial.edits),sum(edit_cost(context,edit) for edit in trial.edits),
                     tuple((edit.span.start.offset,edit.replacement) for edit in trial.edits),trial.category,trial.basis))
    proposals = []
    for trial in ordered[:MAX_TRIALS]:
        if monotonic()>=program.deadline:
            return (),report | {"status":"ANALYSIS_LIMITED"}
        report["trials"]+=1
        if not accepted(context,program,spec,trial,digits):
            continue
        report["compatible_candidates"]+=1
        if len(proposals)>=MAX_PROPOSALS:
            continue
        report["witnesses"].append({"category":trial.category,"edits":[
            {"span":edit.span.to_dict(),"replacement":edit.replacement} for edit in trial.edits]})
        proposals.append(Proposal(trial.edits,trial.category,(Evidence("FINITE_CONSTRAINT_WITNESS",trial.basis,trial.edits[0].span),),
                                  "Check the proposal on the isolated worker before reviewing the full diff.",
                                  "ControlFlow","endpoint",type_match=True,counter_evidence=(
                                      Evidence("FINITE_DOMAIN","These constraints cover the supplied typed inputs.",trial.edits[0].span),)))
    report["status"] = ("MULTIPLE_COMPATIBLE_EDITS" if report["compatible_candidates"]>1 else
                        "COMPATIBLE_EDIT" if proposals else "NO_COMPATIBLE_EDIT")
    return tuple(proposals),report
