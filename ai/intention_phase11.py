"""Bounded relational repair over checked source-local observations."""
from dataclasses import dataclass
from math import gcd
from time import monotonic

from analysis_evidence.function_summary import analyze_program
from compiler import ast_nodes as ast
from compiler.source_location import SourceSpan

from .intention_candidates import Edit, Evidence, Proposal, apply_edits, point
from .intention_context import build_context
from .intention_phase8 import ProjectionLimit, UnsupportedProjection, edit_cost
from .intention_phase10 import MAX_PROPOSALS, MAX_TRIALS
from .intention_phase10_flow import assignment, literal, walk
from .intention_phase105 import aggregate_trials, endpoint_trials, observations, rotation_shape, Trial
from .intention_phase95_flow import project
from .intention_phase11_flow import RelationalProgress, RelationalProjection, binary

INTERPOLATION = "INTERPOLATION_RELATIONAL_CONSTRAINT"
HELPER = "ZERO_MAGNITUDE_HELPER_CONSTRAINT"
CYCLIC = "CYCLIC_TIE_CONSTRAINT"
RANGE = "COORDINATED_RANGE_CONSTRAINT"
COMPONENTS = frozenset({"relational","interpolation","helper","cyclic","range"})
CATEGORIES = frozenset({INTERPOLATION,HELPER,CYCLIC,RANGE})


@dataclass(frozen=True,slots=True)
class RelationFact:
    kind: str
    span: SourceSpan
    function: str
    bindings: tuple
    assumptions: tuple
    samples: tuple
    compiler: tuple = ()
    hypothesis: str | None = None

    def to_dict(self):
        return {"kind":self.kind,"span":self.span.to_dict(),"function":self.function,
                "bindings":list(self.bindings),"assumptions":list(self.assumptions),
                "samples":list(self.samples),"compiler":list(self.compiler),
                "hypothesis":self.hypothesis,"scope":"SUPPLIED_EXAMPLES_ONLY",
                "completeness":"BOUNDED_SAMPLES" if self.samples else "STATIC_ONLY"}


def sample(model,spec):
    rows = []
    for example in spec.examples:
        watcher = RelationalProgress(model)
        result = project(model,spec.function,example.args,observer=watcher,inspect=watcher.inspection)
        rows.append((result,watcher.inspection))
    return rows


def function_of(model,node):
    return next(record.function.name for record in model.context.nodes if record.node is node and record.function)


def cell_facts(model,rows):
    for relation in model.relations.values():
        if relation.kind!="neighbor":
            continue
        node=relation.node
        name=function_of(model,node)
        observed=[]
        for i,(readings,(_,witness)) in enumerate(zip(observations(relation,rows),rows,strict=True),1):
            if readings:
                left,a,b,_,right,_=readings[0]
                observed.append({"input":i,"left_index":left,"right_index":right,"left_value":a,"right_value":b,
                                 "equal":a==b,"cfg_path":witness.paths.get(name,[])})
        extent=model.arrays[relation.array]["length"]
        yield RelationFact("cells",node.span,name,(model.bindings.symbols[relation.array].name,),
                           (),tuple(observed),(f"Same lexical array, extent {extent}",))


def facts_for_interpolation(model,spec,rows,facts):
    source = model.context
    for info in model.interpolations:
        upper,lower,width,offset = info.values
        expression = info.declaration.initializer.right
        division = expression.left if info.early_division else expression
        function = function_of(model,info.declaration)
        observed,zero = [],[]
        for i,(example,(result,witness)) in enumerate(zip(spec.examples,rows,strict=True),1):
            right,left = (witness.reads.get(id(node)) for node in (upper,lower))
            if right is None or left is None:
                continue
            hi,hi_value,cells = right
            lo,lo_value,other = left
            if cells!=other or None in cells[lo:hi+1] or not 0<=lo<=hi<info.extent:
                continue
            interval = cells[lo:hi+1]
            ordered = all(a<=b for a,b in zip(interval,interval[1:]))
            denominator = hi_value-lo_value
            observed.append({"input":i,"low":lo,"high":hi,"lower_value":lo_value,"upper_value":hi_value,
                             "denominator":denominator,"ordered":ordered,"cfg_path":witness.paths.get(function,[])})
            if result.value is None and any(origin==id(division) and op=="/" and divisor==0
                                            for origin,op,_,divisor in witness.faults):
                zero.append(ordered and denominator==0 and example.expected_return==lo)
        binding_names = tuple(model.bindings.symbols[key].name for key in (info.low,info.high,info.key,info.array))
        facts.append(RelationFact("interpolation",info.denominator.span,function,binding_names,
                                  ("The entered interval is ordered on the evidenced inputs.",),tuple(observed),
                                  (f"Fixed extent of {info.extent} cells","Signed checked arithmetic"),
                                  "Equal endpoint values may require a lower-endpoint return."))
        if not observed or not all(row["ordered"] for row in observed):
            continue
        repairs=[]
        if zero and all(zero) and sum(row["denominator"]!=0 for row in observed)>=1:
            low_name = binding_names[0]
            guard = f"if ({source.text(upper.span)} == {source.text(lower.span)}) {{ return {low_name}; }}\n    "
            repairs.append(Edit(point(info.declaration.span.start),guard))
        reordered = None
        if info.early_division:
            reordered = Edit(expression.span,f"(({source.text(width.span)})*({source.text(offset.span)}))/({source.text(info.denominator.span)})")
        edit_sets = [(edit,) for edit in repairs]
        if reordered is not None:
            edit_sets.append((reordered,))
            if repairs:
                edit_sets.append((repairs[0],reordered))
        for edits in edit_sets:
            yield Trial(INTERPOLATION,edits,"Checked endpoint relations support the equal-value guard or the revised probe.")


def helper_trials(model,spec,rows,facts):
    if spec.return_type!="bool":
        return
    function = model.functions[spec.function].function
    params = function.parameters
    if len(params)!=2 or any(param.type_name!="int" for param in params):
        return
    for node in walk(function.body):
        if not isinstance(node,ast.ReturnStatement) or not binary(node.value,"=="):
            continue
        comparison = node.value
        call,one = (comparison.left,comparison.right) if isinstance(comparison.left,ast.FunctionCall) else (comparison.right,comparison.left)
        if not isinstance(call,ast.FunctionCall) or not isinstance(call.callee,ast.Identifier) or not literal(one,1):
            continue
        if {model.index(arg) for arg in call.arguments}!={model.bindings.declaration(param) for param in params} or len(call.arguments)!=2:
            continue
        name = call.callee.name
        if name not in model.modulo and name not in model.linear_helpers:
            continue
        boundary,ordinary,details = [],[],[]
        for i,(example,(result,witness)) in enumerate(zip(spec.examples,rows,strict=True),1):
            a,b=example.args
            calls=witness.calls.get(name,[])
            if not calls or result.value is None:
                continue
            if not a or not b:
                boundary.append((a,b,example.expected_return==(abs(a or b)==1),result.value!=example.expected_return))
            else:
                ordinary.append(example.expected_return==(gcd(a,b)==1)==result.value)
            details.append({"input":i,"arguments":[a,b],"helper_calls":[[list(args),value] for args,value in calls],
                            "observed":result.value,"cfg_path":witness.paths.get(spec.function,[])})
        if not boundary or not all(row[2] for row in boundary) or len(ordinary)<2 or not all(ordinary):
            continue
        if not (any(a==0 and b for a,b,*_ in boundary) and any(b==0 and a for a,b,*_ in boundary)
                and any(abs(a or b)!=1 for a,b,*_ in boundary)):
            continue
        a,b=(param.name for param in params)
        facts.append(RelationFact("helper",comparison.span,spec.function,(a,b,name),
                                 ("The supplied zero inputs define a unity test by magnitude.",),tuple(details),
                                 ("Pure bounded helper","Typed boolean return"),"Return the observed magnitude-one relation on zero inputs."))
        if not any(row[3] for row in boundary):
            continue
        token=next((token for token in model.context.parsed.tokens if token.lexeme=="{"
                    and token.span.start.offset==function.body.span.start.offset),None)
        if token:
            guard = f"\n    if ({a} == 0 || {b} == 0) {{ return {a} == 1 || {a} == -1 || {b} == 1 || {b} == -1; }}\n"
            yield Trial(HELPER,(Edit(point(token.span.end),guard),),
                        "The observed helper and separately varied zero inputs support a magnitude-one result.")


def cyclic_trials(model,spec,rows,facts):
    for rel in model.relations.values():
        if rel.kind!="rotation":
            continue
        shape = rotation_shape(model,rel)
        if shape is None:
            continue
        observations_by_case=observations(rel,rows)
        extent,wanted,latch=shape
        if latch is not None or rel.node.operator!=wanted:
            continue
        checks,details = [],[]
        for i,(example,values,(_,witness)) in enumerate(zip(spec.examples,observations_by_case,rows,strict=True),1):
            if not values:
                continue
            cells=values[0][3]
            if None in cells or len(cells)!=extent or any(row[3]!=cells for row in values):
                continue
            descents=[j for j in range(extent) if cells[j]>cells[(j+1)%extent]]
            acceptable=(type(example.expected_return) is int and 0<=example.expected_return<extent
                        and cells[example.expected_return]==min(cells))
            checks.append(len(descents)<=1 and acceptable)
            details.append({"input":i,"extent":extent,"descents":descents,
                            "duplicates":len(set(cells))!=extent,"equal_compared":any(row[1]==row[2] for row in values),
                            "cfg_path":witness.paths.get(function_of(model,rel.node),[])})
        function=function_of(model,rel.node)
        facts.append(RelationFact("cyclic",rel.node.span,function,(model.bindings.symbols[rel.array].name,),
                                 ("Input cells form a cyclic nondecreasing sequence on evidenced paths.",
                                  "Supplied positions must reference a minimum value."),tuple(details),
                                  (f"Fixed extent of {extent} cells",),"Refine an equal comparison by one checked endpoint."))
        if len(checks)!=len(rows) or not all(checks) or sum(row["equal_compared"] for row in details)<2:
            continue
        branch=next((node for node in model.nodes.values() if isinstance(node,ast.IfStatement)
                     and node.condition is rel.node and isinstance(node.else_branch,ast.Block)),None)
        if branch is None or len(branch.else_branch.statements)!=1:
            continue
        upper=assignment(branch.else_branch.statements[0])
        if not isinstance(upper,ast.Assignment) or model.index(upper.target) not in {
                model.index(rel.node.left.index),model.index(rel.node.right.index)}:
            continue
        first,second=(model.context.text(child.span) for child in (rel.node.left,rel.node.right))
        endpoint=model.context.text(upper.target.span)
        # Inserting before the original else body preserves the original
        # branch and its source-located assignments.
        insertion=f" if ({first} == {second}) {{ {endpoint}--; }} else "
        yield Trial(CYCLIC,(Edit(point(branch.else_branch.span.start),insertion),),
                    "Observed duplicate comparisons support a bounded equal-endpoint refinement.")


def range_trials(model,spec,rows,facts):
    note=[]
    for start in aggregate_trials(model,spec,note):
        origin=start.edits[0].replacement
        edit=start.edits[0]
        loop=next((node for node in model.nodes.values() if isinstance(node,ast.ForStatement)
                   and isinstance(node.initializer,ast.VariableDeclaration)
                   and node.initializer.initializer is not None and node.initializer.initializer.span==edit.span),None)
        if loop is None or not isinstance(loop.condition,ast.BinaryExpression):
            continue
        binding=model.context.visible_at(edit.span.start.offset).get(origin)
        if binding is None:
            continue
        limit=loop.condition.right
        if not binary(limit,"+") or model.index(limit.left)!=binding.id or not isinstance(limit.right,ast.Literal):
            continue
        induction=model.bindings.declaration(loop.initializer)
        for access in walk(loop.body):
            if not isinstance(access,ast.ArrayAccess) or not binary(access.index,"-") or not model.array_info(access):
                continue
            index=access.index
            if model.index(index.left)!=induction or not literal(index.right,0):
                continue
            if model.context.visible_at(index.span.start.offset).get(origin)!=binding:
                continue
            function=spec.function
            supporting=tuple({"input":i,"issue":result.issue,"cfg_path":witness.paths.get(function,[])}
                             for i,(result,witness) in enumerate(rows,1))
            facts.append(RelationFact("range",index.span,function,(origin,model.bindings.symbols[induction].name),
                                     ("The same reaching origin determines iteration and cell coordinates.",),supporting,
                                     (f"Fixed extent of {model.array_info(access)[1]} cells",),
                                     "Rebase both traversal and indexed access."))
            yield Trial(RANGE,(edit,Edit(index.right.span,origin)),
                        "The reaching origin coordinates both the iteration start and the checked cell offset.")


def accepted(context,program,spec,trial,enabled):
    source = apply_edits(context.source,trial.edits)
    candidate = build_context(source,None)
    if not candidate.compiler_valid:
        return False
    revised = analyze_program(candidate,program.deadline)
    if revised.status!="AVAILABLE":
        return False
    model = RelationalProjection(candidate,revised,enabled)
    try:
        model.compile(spec.function)
        for example in spec.examples:
            result=project(model,spec.function,example.args,observer=RelationalProgress(model,strict=True))
            if type(result.value) is not type(example.expected_return) or result.value!=example.expected_return:
                return False
    except (UnsupportedProjection,ProjectionLimit):
        return False
    return True


def synthesize(context,program,spec,enabled):
    report={"status":"INCOMPLETE_SPECIFICATION","scope":"SUPPLIED_EXAMPLES_ONLY","components":sorted(enabled),
            "facts":[],"witnesses":[],"trials":0,"compatible_candidates":0}
    if not enabled or len({row.args for row in spec.examples})<3 or spec.return_type not in {"int","bool"}:
        return (),report
    if program.status!="AVAILABLE" or context.parsed.ast.globals:
        return (),report | {"status":"UNSUPPORTED_PROJECTION"}
    model=RelationalProjection(context,program,enabled)
    try:
        model.compile(spec.function)
        rows=sample(model,spec)
    except UnsupportedProjection:
        return (),report | {"status":"UNSUPPORTED_PROJECTION"}
    except ProjectionLimit:
        return (),report | {"status":"ANALYSIS_LIMITED"}
    report["sample_issues"]=[result.issue for result,_ in rows]
    facts,trials = [],[]
    if "relational" in enabled:
        endpoint=[]
        trials.extend(endpoint_trials(model,rows,spec,endpoint))
        report["endpoint_contracts"]=endpoint[:16]
        facts.extend(cell_facts(model,rows))
    for component,build in (("interpolation",facts_for_interpolation),("helper",helper_trials),
                            ("cyclic",cyclic_trials),("range",range_trials)):
        if component in enabled:
            trials.extend(build(model,spec,rows,facts))
    for fact in facts[:48]:
        visible=context.visible_at(fact.span.start.offset)
        report["facts"].append(fact.to_dict() | {"lexical_bindings":[{"name":name,"id":visible[name].id}
                                                                  for name in fact.bindings if name in visible]})
    if all(type(result.value) is type(example.expected_return) and result.value==example.expected_return
           for (result,_),example in zip(rows,spec.examples,strict=True)):
        return (),report | {"status":"CONSTRAINTS_ALREADY_AGREE"}
    ordered=sorted(set(trials),key=lambda trial:(len(trial.edits),sum(edit_cost(context,edit) for edit in trial.edits),
                   tuple((edit.span.start.offset,edit.replacement) for edit in trial.edits),trial.category,trial.basis))
    proposals=[]
    for trial in ordered[:MAX_TRIALS]:
        if monotonic()>=program.deadline:
            return (),report | {"status":"ANALYSIS_LIMITED"}
        report["trials"]+=1
        if not accepted(context,program,spec,trial,enabled):
            continue
        report["compatible_candidates"]+=1
        if len(proposals)>=MAX_PROPOSALS:
            continue
        report["witnesses"].append({"category":trial.category,"edits":[{"span":edit.span.to_dict(),"replacement":edit.replacement}
                                                                      for edit in trial.edits]})
        proposals.append(Proposal(trial.edits,trial.category,(Evidence("FINITE_CONSTRAINT_WITNESS",trial.basis,trial.edits[0].span),),
                                  "Verify the complete candidate against supplied observations before approval.",
                                  "ControlFlow","relational",type_match=True,counter_evidence=(
                                      Evidence("FINITE_DOMAIN","The relational observations cover the supplied typed examples.",trial.edits[0].span),)))
    report["status"]=("MULTIPLE_COMPATIBLE_EDITS" if report["compatible_candidates"]>1 else
                      "COMPATIBLE_EDIT" if proposals else "NO_COMPATIBLE_EDIT")
    return tuple(proposals),report
