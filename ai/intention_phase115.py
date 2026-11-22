"""Checked endpoint, first-minimum, and aggregate dependency repairs."""
from time import monotonic

from compiler import ast_nodes as ast

from .intention_candidates import Edit, Evidence, Proposal, point
from .intention_phase8 import ProjectionLimit, UnsupportedProjection, edit_cost
from .intention_phase10 import MAX_PROPOSALS, MAX_TRIALS
from .intention_phase10_flow import assignment, literal, walk
from .intention_phase105 import aggregate_trials, observations, Trial
from .intention_phase11 import accepted, function_of, sample
from .intention_phase11_flow import RelationalProjection, binary

ENDPOINT = "EXPLICIT_ENDPOINT_CONSTRAINT"
CYCLIC = "FIRST_CYCLIC_MINIMUM_CONSTRAINT"
RANGE = "COORDINATED_EXTREMA_SEED_CONSTRAINT"
COMPONENTS = frozenset({"endpoint","cyclic","range","interpolation"})
CATEGORIES = frozenset({ENDPOINT,CYCLIC,RANGE})
BASE_PROJECTION = frozenset({"relational","interpolation","helper","cyclic","range"})


def endpoint_trials(model,spec,rows,facts):
    for name,interval in model.recursive.items():
        if name==spec.function or interval.missing_base:
            continue
        function=model.functions[name].function
        calls=[call for call in model.nodes.values() if isinstance(call,ast.FunctionCall)
               and isinstance(call.callee,ast.Identifier) and call.callee.name==name
               and id(call) not in interval.calls]
        if not calls or any(len(call.arguments)!=len(function.parameters) for call in calls):
            continue
        lo=model.bindings.symbols[interval.low].name
        hi=model.bindings.symbols[interval.high].name
        for branch in function.body.statements:
            if not isinstance(branch,ast.IfStatement) or branch.span.end.offset>interval.span.start.offset or branch.else_branch:
                continue
            guard=branch.condition
            if not (binary(guard,"<") and model.index(guard.left)==interval.high and literal(guard.right,0)
                    or binary(guard,">") and literal(guard.left,0) and model.index(guard.right)==interval.high):
                continue
            body=branch.then_branch
            statements=body.statements if isinstance(body,ast.Block) else (body,)
            if len(statements)!=1:
                continue
            reset=assignment(statements[0])
            if not (isinstance(reset,ast.Assignment) and reset.operator=="=" and model.index(reset.target)==interval.high
                    and literal(reset.value,interval.length-int(interval.inclusive))):
                continue
            inputs=[]
            for i,(_,witness) in enumerate(rows,1):
                frames=witness.frames.get(name,[])
                if not frames:
                    continue
                start=frames[0]
                if not 0<=start[0]<interval.length or not 0<=start[1]<=interval.length-int(interval.inclusive):
                    break
                inputs.append({"input":i,"start":start,"negative_empty_endpoint":any(
                    0<=a and b<0 and b<a for a,b in frames[1:])})
            else:
                if len(inputs)<2:
                    continue
                facts.append({"kind":"endpoint","span":branch.span.to_dict(),"bindings":[lo,hi],
                              "contract":"Explicit signed endpoint","extent":interval.length,"samples":inputs,
                              "assumption":"The compiled call sites pass actual endpoints. An empty interval reaches the separate base result."})
                if any(row["negative_empty_endpoint"] for row in inputs):
                    yield Trial(ENDPOINT,(Edit(branch.span,""),),
                                "A concrete negative endpoint denotes an empty interval at the compiled calls.")


def interval_extent(model,interval,function):
    declarations={model.bindings.declaration(node):node.initializer for node in function.body.statements
                  if isinstance(node,ast.VariableDeclaration) and node.span.start.offset<interval.span.start.offset}
    if not literal(declarations.get(interval.low),0):
        return None
    high=declarations.get(interval.high)
    if literal(high,interval.length-1):
        return (None,interval.length)
    if not (binary(high,"-") and literal(high.right,1)):
        return None
    binding=model.index(high.left)
    for i,param in enumerate(function.parameters):
        if model.bindings.declaration(param)==binding:
            return i,interval.length
    return None


def cyclic_trials(model,spec,rows,facts):
    entry=model.functions[spec.function].function
    for relation in model.relations.values():
        if relation.kind!="rotation" or function_of(model,relation.node)!=spec.function:
            continue
        node=relation.node
        left,right=node.left,node.right
        interval=next((interval for interval in model.intervals.get(spec.function,())
                       if {model.index(left.index),model.index(right.index)}=={interval.midpoint,interval.high}),None)
        if interval is None or interval.inclusive:
            continue
        extent=interval_extent(model,interval,entry)
        tail=entry.body.statements[-1]
        if extent is None or not isinstance(tail,ast.ReturnStatement) or model.index(tail.value)!=interval.low:
            continue
        coordinate,physical=extent
        supporting=[]
        for i,(example,readings,(original,_)) in enumerate(zip(spec.examples,observations(relation,rows),rows,strict=True),1):
            size=physical if coordinate is None else example.args[coordinate]
            if type(size) is not int or not 0<=size<=physical:
                break
            if size<=1 and not readings and original.value==example.expected_return:
                supporting.append({"input":i,"extent":size,"first":0 if size==1 else None,"minima":[],"agrees":True})
                continue
            if not readings or type(example.expected_return) is not int:
                break
            values=readings[0][3][:size]
            if None in values or any(other[3][:size]!=values for other in readings):
                break
            if sum(values[j]>values[(j+1)%size] for j in range(size))>1:
                break
            minimum=min(values)
            minima=[position for position,value in enumerate(values) if value==minimum]
            if example.expected_return not in minima or original.value not in minima:
                break
            supporting.append({"input":i,"extent":size,"first":minima[0],"minima":minima,
                               "agrees":original.value==example.expected_return,"expects_first":example.expected_return==minima[0]})
        else:
            variants=[item for item in supporting if len(item["minima"])>1]
            if len(variants)<2:
                continue
            first=all(item["expects_first"] for item in supporting if item["minima"])
            array=model.bindings.symbols[relation.array].name
            name=model.bindings.symbols[interval.low].name
            facts.append({"kind":"cyclic","span":tail.span.to_dict(),"bindings":[array,name],"extent":physical,
                          "contract":"First minimum" if first else "Any matching minimum","samples":supporting})
            if first and any(not item["agrees"] for item in variants) and all(
                    item["agrees"] or item["first"]==0 for item in variants):
                edit=Edit(point(tail.span.start),f"if ({name} > 0 && {array}[{name}] == {array}[0]) {{ return 0; }} ")
                yield Trial(CYCLIC,(edit,),"On the observed cyclic seam the first matching minimum is at index zero.")


def extrema(model,function):
    evidence={}
    for scan in function.body.statements:
        if not isinstance(scan,ast.ForStatement):
            continue
        for branch in walk(scan.body):
            if not isinstance(branch,ast.IfStatement) or branch.else_branch:
                continue
            test=branch.condition
            if not isinstance(test,ast.BinaryExpression) or test.operator not in {"<",">"}:
                continue
            cell,value=test.left,test.right
            if not isinstance(cell,ast.ArrayAccess) or not model.array_info(cell) or not model.index(value):
                continue
            body=branch.then_branch
            body=body.statements if isinstance(body,ast.Block) else (body,)
            if len(body)!=1:
                continue
            update=assignment(body[0])
            if not isinstance(update,ast.Assignment) or update.operator!="=" or not isinstance(update.value,ast.ArrayAccess):
                continue
            binding=model.index(value)
            if (model.index(update.target)==binding and model.array_info(update.value)==model.array_info(cell)
                    and model.index(update.value.index)==model.index(cell.index)):
                evidence[(binding,test.operator)]=(scan.span,model.array_info(cell)[0])
    return evidence


def range_trials(model,spec,rows,facts):
    function=model.functions[spec.function].function
    end=function.body.statements[-1]
    if not isinstance(end,ast.ReturnStatement) or not model.index(end.value):
        return
    accumulator=model.index(end.value)
    seed=next((part for part in function.body.statements if isinstance(part,ast.VariableDeclaration)
               and model.bindings.declaration(part)==accumulator and isinstance(part.initializer,ast.Literal)),None)
    if seed is None:
        return
    reached=extrema(model,function)
    for start in aggregate_trials(model,spec,[]):
        origin=start.edits[0]
        loop=next((part for part in function.body.statements if isinstance(part,ast.ForStatement)
                   and isinstance(part.initializer,ast.VariableDeclaration) and part.initializer.initializer
                   and part.initializer.initializer.span==origin.span),None)
        if loop is None or seed.span.end.offset>loop.span.start.offset:
            continue
        updates=[assignment(node) for node in walk(loop.body) if isinstance(node,ast.ExpressionStatement)]
        if not any(isinstance(node,ast.Assignment) and node.operator=="=" and model.index(node.target)==accumulator
                   and isinstance(node.value,ast.FunctionCall) and isinstance(node.value.callee,ast.Identifier)
                   and node.value.callee.name in model.digit_sites
                   and any(model.index(arg)==accumulator for arg in node.value.arguments) for node in updates):
            continue
        visible=model.context.visible_at(origin.span.start.offset)
        minimum=visible.get(origin.replacement)
        lower=reached.get((minimum.id,"<")) if minimum else None
        if lower is None:
            continue
        for (binding,operator),(span,array) in reached.items():
            name=model.bindings.symbols[binding].name
            before=model.context.visible_at(seed.initializer.span.start.offset)
            if operator!=">" or array!=lower[1] or span.end.offset>seed.span.start.offset or before.get(name)!=visible.get(name):
                continue
            if name not in before or before[name].id!=binding:
                continue
            facts.append({"kind":"range","span":loop.span.to_dict(),"bindings":[origin.replacement,name,seed.name],
                          "contract":"Shared extrema for the traversal and accumulator seed",
                          "samples":[{"input":i,"issue":result.issue} for i,(result,_) in enumerate(rows,1)]})
            yield Trial(RANGE,(Edit(seed.initializer.span,name),origin),
                        "The already-scanned minimum and maximum supply the traversal and helper seed.")


def synthesize(context,program,spec,enabled,prior):
    report={"status":"INCOMPLETE_SPECIFICATION","scope":"SUPPLIED_EXAMPLES_ONLY","facts":[],"trials":0,"compatible_candidates":0}
    if "interpolation" in enabled:
        options=[row for row in prior.get("witnesses",[]) if row["category"]=="INTERPOLATION_RELATIONAL_CONSTRAINT"]
        if len(options)>1:
            report["facts"].append({"kind":"interpolation","contract":"Several candidates match discovery","alternatives":len(options),
                                    "assumption":"Disagreement probes have no trusted output. Both repairs remain available for review.","samples":[]})
    if not enabled or len({row.args for row in spec.examples})<3 or spec.return_type!="int":
        return (),report
    if program.status!="AVAILABLE" or context.parsed.ast.globals:
        return (),report | {"status":"UNSUPPORTED_PROJECTION"}
    if not enabled & {"endpoint","cyclic","range"}:
        return (),report | {"status":"OBSERVATION_ONLY"}
    model=RelationalProjection(context,program,BASE_PROJECTION)
    try:
        model.compile(spec.function)
        rows=sample(model,spec)
    except UnsupportedProjection:
        return (),report | {"status":"UNSUPPORTED_PROJECTION"}
    except ProjectionLimit:
        return (),report | {"status":"ANALYSIS_LIMITED"}
    trials=[]
    for key,build in (("endpoint",endpoint_trials),("cyclic",cyclic_trials),("range",range_trials)):
        if key in enabled:
            trials.extend(build(model,spec,rows,report["facts"]))
    del report["facts"][32:]
    if all(type(result.value) is type(example.expected_return) and result.value==example.expected_return
           for (result,_),example in zip(rows,spec.examples,strict=True)):
        return (),report | {"status":"CONSTRAINTS_ALREADY_AGREE"}
    proposals=[]
    order=sorted(set(trials),key=lambda row:(sum(edit_cost(context,edit) for edit in row.edits),
                 tuple((edit.span.start.offset,edit.replacement) for edit in row.edits),row.category))
    for trial in order[:MAX_TRIALS]:
        if monotonic()>=program.deadline:
            return (),report | {"status":"ANALYSIS_LIMITED"}
        report["trials"]+=1
        if not accepted(context,program,spec,trial,BASE_PROJECTION):
            continue
        report["compatible_candidates"]+=1
        if len(proposals)<MAX_PROPOSALS:
            proposals.append(Proposal(trial.edits,trial.category,
                             (Evidence("FINITE_CONSTRAINT_WITNESS",trial.basis,trial.edits[0].span),),
                             "Review the complete verified source diff before approving.",
                             "ControlFlow","reliability",type_match=True,counter_evidence=(
                                 Evidence("FINITE_DOMAIN","The candidate agrees on the supplied examples.",trial.edits[0].span),)))
    report["status"]=("MULTIPLE_COMPATIBLE_EDITS" if report["compatible_candidates"]>1
                      else "COMPATIBLE_EDIT" if proposals else "AMBIGUOUS_DISCOVERY" if any(
                          fact["kind"]=="interpolation" for fact in report["facts"]) else "NO_COMPATIBLE_EDIT")
    return tuple(proposals),report
