"""Progress and fixed-cell evidence layered over the Phase 9.5 CFG projection."""
from dataclasses import dataclass

from ai.intention_context import ast_children
from analysis_evidence.dataflow import effects
from compiler import ast_nodes as ast
from compiler.source_location import SourceSpan

from .intention_candidates import Edit, point
from .intention_phase8 import Change, Projector, Term, UnsupportedProjection
from .intention_phase95_flow import FlowProjection, InvalidSample

ARRAY = "FIXED_ARRAY_INDEX_CONSTRAINT"
SEARCH = "SEARCH_INTERVAL_CONSTRAINT"
EXPANSION = "EXPANDING_HANDOFF_CONSTRAINT"
HELPER = "HELPER_PROGRESS_CONSTRAINT"
RANGE = "DERIVED_RANGE_CONSTRAINT"


def walk(node):
    pending = [node]
    while pending:
        current = pending.pop()
        yield current
        pending.extend(reversed([child for _,child in ast_children(current)]))


def literal(node,value):
    return isinstance(node,ast.Literal) and type(node.value) is int and node.value==value


def assignment(node):
    return node.expression if isinstance(node,ast.ExpressionStatement) else node


@dataclass(frozen=True, slots=True)
class Interval:
    low: str
    high: str
    midpoint: str
    length: int
    span: SourceSpan
    inclusive: bool
    positions: tuple = ()
    calls: tuple = ()
    missing_base: bool = False


@dataclass(frozen=True, slots=True)
class DynamicLoop:
    mode: str
    slot: int
    other: int | None
    span: SourceSpan
    bound: str
    inclusive: bool = False
    extent: int | None = None


class SearchProjection(FlowProjection):
    def __init__(self,context,program,enabled):
        inherited = {"helpers"}
        if "range" in enabled:
            inherited.add("range")
        super().__init__(context,program,frozenset(inherited))
        self.features = enabled
        self.intervals = {}
        self.recursive = {}
        self.expansions = {}
        self.modulo = set()
        self.offsets = {}
        self.fallbacks = {}
        self.arrays = {}
        self.sites = {}
        self.range_offsets = {}
        self.base_origins = {}
        self.sentinel = None

    def register(self,node,span,replacement,category,action,value):
        Projector.change(self,node,span,replacement,category,action,value)

    def index(self,node):
        return self.identifier(node)

    def midpoint(self,node):
        if not isinstance(node,ast.BinaryExpression):
            return None
        if node.operator=="/" and literal(node.right,2):
            inner = node.left
            if isinstance(inner,ast.BinaryExpression) and inner.operator=="+":
                a,b = self.index(inner.left),self.index(inner.right)
                if a and b and a!=b:
                    return {a,b}
        if node.operator=="+":
            head = self.index(node.left)
            inner = node.right
            if isinstance(inner,ast.BinaryExpression) and inner.operator=="/" and literal(inner.right,2):
                diff = inner.left
                if isinstance(diff,ast.BinaryExpression) and diff.operator=="-" and self.index(diff.right)==head:
                    high = self.index(diff.left)
                    if head and high and head!=high:
                        return {head,high}
        return None

    def array_info(self,indexed):
        symbol = self.bindings.identifiers.get(id(indexed.array))
        if symbol is None or symbol.id in self.bindings.globals:
            return None
        size = symbol.array_size
        if type(size) is int and size>0:
            return symbol.id, size
        return None

    def interval(self,scope,guard,*,recursive=False):
        if not isinstance(guard,ast.BinaryExpression) or guard.operator not in {"<","<=",">",">="}:
            return None
        a,b = self.index(guard.left),self.index(guard.right)
        if not a or not b or a==b:
            return None
        if recursive:
            low,high = (b,a) if guard.operator in {"<","<="} else (a,b)
            inclusive = guard.operator in {"<",">"}
        else:
            low,high = (a,b) if guard.operator in {"<","<="} else (b,a)
            inclusive = guard.operator in {"<=",">="}
        nodes = list(walk(scope))
        mids = [node for node in nodes if isinstance(node,ast.VariableDeclaration) and self.midpoint(node.initializer)=={low,high}]
        if len(mids)!=1:
            return None
        mid = self.bindings.declaration(mids[0])
        indexed = [self.array_info(node) for node in nodes if isinstance(node,ast.ArrayAccess) and self.index(node.index)==mid]
        indexed = {item for item in indexed if item is not None}
        if len(indexed)!=1:
            return None
        _,length = indexed.pop()
        return Interval(low,high,mid,length,guard.span,inclusive)

    def prepare(self,name):
        item = self.functions.get(name)
        if item is None:
            raise UnsupportedProjection
        function = item.function
        nodes = list(walk(function.body))
        # The compiler's reachable graph still controls the projected path.
        for node in nodes:
            if isinstance(node,(ast.ArrayDeclaration,ast.ArrayAccess)):
                self.sites[id(node)] = node.span
            if isinstance(node,ast.ArrayDeclaration):
                key = self.bindings.declaration(node)
                if key is not None and isinstance(node.size,ast.Literal):
                    self.arrays[key] = {"function":name,"name":node.name,"binding":key,"length":node.size.value,
                                        "element_type":node.type_name,"span":node.span.to_dict()}
        if "search" not in self.features:
            return
        calls = [node for node in nodes if isinstance(node,ast.FunctionCall)
                 and isinstance(node.callee,ast.Identifier) and node.callee.name==name]
        if calls:
            returns = {id(node.value) for node in nodes if isinstance(node,ast.ReturnStatement)}
            if any(id(call) not in returns for call in calls):
                raise UnsupportedProjection
            parameters = [self.bindings.declaration(parameter) for parameter in function.parameters]
            for statement in function.body.statements:
                if not isinstance(statement,ast.IfStatement) or statement.else_branch:
                    continue
                body = statement.then_branch
                block = body.statements if isinstance(body,ast.Block) else [body]
                if len(block)!=1 or not isinstance(block[0],ast.ReturnStatement):
                    continue
                returned=block[0].value
                if not (isinstance(returned,ast.UnaryExpression) and returned.operator=="-"
                        and isinstance(returned.operand,ast.Literal) and type(returned.operand.value) is int
                        and returned.operand.value>0):
                    continue
                interval = self.interval(function.body,statement.condition,recursive=True)
                if interval and {interval.low,interval.high}<=set(parameters):
                    positions=(parameters.index(interval.low),parameters.index(interval.high))
                    self.recursive[name] = Interval(interval.low,interval.high,interval.midpoint,interval.length,
                                                    interval.span,interval.inclusive,positions,tuple(id(call) for call in calls))
                    self.intervals[name] = [self.recursive[name]]
                    break
            if name not in self.recursive:
                self.missing_base(function,parameters,calls)
            if name not in self.recursive:
                raise UnsupportedProjection

    def missing_base(self,function,parameters,calls):
        if self.sentinel is None:
            return
        nodes=list(walk(function.body))
        for declaration in (node for node in nodes if isinstance(node,ast.VariableDeclaration)):
            endpoints=self.midpoint(declaration.initializer)
            if not endpoints or not endpoints<=set(parameters):
                continue
            mid=self.bindings.declaration(declaration)
            positions={}
            for position,parameter in enumerate(parameters):
                if parameter not in endpoints:
                    continue
                modified=[call.arguments[position] for call in calls if self.index(call.arguments[position])!=parameter]
                if len(modified)!=1:
                    continue
                expr=modified[0]
                if (isinstance(expr,ast.BinaryExpression) and expr.operator in {"+","-"}
                        and self.index(expr.left)==mid and literal(expr.right,1)):
                    positions[expr.operator]=position
            if len(positions)!=2:
                continue
            arrays={self.array_info(node) for node in nodes if isinstance(node,ast.ArrayAccess) and self.index(node.index)==mid}
            arrays.discard(None)
            if len(arrays)!=1:
                continue
            lower,upper=positions["+"],positions["-"]
            # The two observed call updates define the inclusive convention.
            # Leave unusual existing endpoint checks to the legacy engine.
            if any(isinstance(node,ast.IfStatement) and isinstance(node.condition,ast.BinaryExpression)
                   and {self.index(node.condition.left),self.index(node.condition.right)}==endpoints
                   for node in nodes):
                return
            _,length=arrays.pop()
            interval=Interval(parameters[lower],parameters[upper],mid,length,declaration.span,True,
                              (lower,upper),tuple(id(call) for call in calls),True)
            opening=next((token for token in self.context.parsed.tokens if token.lexeme=="{"
                          and token.span.start.offset==function.body.span.start.offset),None)
            if opening is None:
                return
            low,high=function.parameters[lower].name,function.parameters[upper].name
            replacement=f"\n    if ({high} < {low}) {{ return {self.sentinel}; }}\n"
            self.register(function,point(opening.span.end),replacement,SEARCH,"entry_guard",self.sentinel)
            self.base_origins[function.name]=id(function)
            self.recursive[function.name]=interval
            self.intervals[function.name]=[interval]
            return

    def compile(self,name):
        if name not in self.models:
            self.prepare(name)
        return super().compile(name)

    def call_term(self,node,name,args):
        if name in self.compiling:
            current = self.recursive.get(name)
            if name!=self.compiling[-1] or current is None or id(node) not in current.calls:
                raise UnsupportedProjection
            return Term("helper", args, value=name)
        self.compile(name)
        interval = self.recursive.get(name)
        if interval:
            lower,upper = interval.positions
            lower_node,upper_node = node.arguments[lower],node.arguments[upper]
            target=interval.length-int(interval.inclusive)
            for original,correct in ((lower_node,0),(upper_node,target)):
                if (isinstance(original,ast.Literal) and type(original.value) is int
                        and abs(original.value-correct)==1):
                    self.register(original,original.span,str(correct),SEARCH,"literal",correct)
        return Term("helper",args,value=name)

    def expression(self,node,locals_,call_depth,depth=0,**flags):
        result = super().expression(node,locals_,call_depth,depth,**flags)
        if isinstance(node,ast.ArrayAccess) and "array" in self.features:
            index = node.index
            # Restrict index edits to a source-local integer offset.
            if (isinstance(index,ast.BinaryExpression) and index.operator in {"+","-"}
                    and self.index(index.left) and isinstance(index.right,ast.Literal)
                    and type(index.right.value) is int and 0<=index.right.value<=16):
                for delta in (-1,1):
                    revised = index.right.value+delta
                    if revised>=0:
                        self.register(index.right,index.right.span,str(revised),ARRAY,"literal",revised)
        if id(node) in self.offsets:
            origin=-id(node)
            for delta in (-1,1):
                # The AST term is retained as an operand of the source edit.
                text=self.context.text(node.span)
                if isinstance(node,ast.Identifier) and delta==1:
                    replacement=f"{text}+1"
                else:
                    replacement=f"({text} {'+' if delta>0 else '-'} 1)"
                self.changes[(origin,node.span.start.offset,node.span.end.offset,replacement)] = Change(
                    origin,Edit(node.span,replacement),EXPANSION,"delta",delta)
            result = Term("identity",(result,),origin=origin)
        if id(node) in self.fallbacks:
            value = self.fallbacks[id(node)]
            self.register(node,node.span,str(value),EXPANSION,"reference",str(value))
            result = Term("identity",(result,),origin=id(node),alternatives=((str(value),Term("literal",value=value)),))
        if id(node) in self.range_offsets:
            target,name = self.range_offsets[id(node)]
            self.register(node,node.span,name,RANGE,"reference",name)
            result = Term("identity",(result,),origin=id(node),alternatives=((name,self.layout[target]),))
        return result

    def boolean(self,node,locals_,depth=0):
        result = super().boolean(node,locals_,depth)
        if ("helper" in self.features and isinstance(node,ast.BinaryExpression) and node.operator in {"==","!="}
                and any(isinstance(part,ast.FunctionCall) and isinstance(part.callee,ast.Identifier)
                        and part.callee.name in self.modulo for part in (node.left,node.right))):
            token=self.operator_span(node)
            if token:
                alternate="!=" if node.operator=="==" else "=="
                self.register(node,token,alternate,HELPER,"operation",alternate)
        return result

    def loop_sites(self,item):
        return sorted(super().loop_sites(item),key=lambda block:block.syntax.span.start.offset)

    def origin_offsets(self,node):
        init=node.initializer
        if not isinstance(init,ast.VariableDeclaration) or not isinstance(init.initializer,ast.Identifier):
            return
        original=init.initializer
        origin=self.index(original)
        induction=self.bindings.declaration(init)
        if not origin or origin==induction:
            return
        writes=effects(node.body,self.bindings,conservative_calls=False).writes
        if origin in writes:
            return
        for part in walk(node.body):
            if isinstance(part,ast.ArrayAccess):
                index=part.index
                if (isinstance(index,ast.BinaryExpression) and index.operator=="-"
                        and self.index(index.left)==induction and literal(index.right,0)):
                    current=self.context.visible_at(index.right.span.start.offset).get(original.name)
                    if current is not None and current.id==origin:
                        self.range_offsets[id(index.right)] = (origin,original.name)

    def iterative_bounds(self,item,node,interval):
        expected=interval.length-int(interval.inclusive)
        for candidate in item.function.body.statements:
            if candidate.span.start.offset>=node.span.start.offset:
                break
            if (isinstance(candidate,ast.VariableDeclaration) and self.bindings.declaration(candidate)==interval.high
                    and isinstance(candidate.initializer,ast.Literal) and type(candidate.initializer.value) is int
                    and abs(candidate.initializer.value-expected)==1):
                init=candidate.initializer
                self.register(init,init.span,str(expected),SEARCH,"literal",expected)

    def loop_site(self,item,block,initializations):
        node=block.syntax
        if isinstance(node,ast.ForStatement):
            result=super().loop_site(item,block,initializations)
            if "range" in self.features:
                self.origin_offsets(node)
            return result
        if not isinstance(node,ast.WhileStatement):
            raise UnsupportedProjection
        guard=node.condition
        interval=self.interval(node.body,guard)
        name=item.function.name
        if interval is not None and self.features & {"search","expansion"}:
            self.intervals.setdefault(name,[]).append(interval)
            if "search" in self.features:
                self.iterative_bounds(item,node,interval)
            if "expansion" in self.features and name in self.expansions:
                self.handoff(item,interval)
            return DynamicLoop("interval",self.layout[interval.low].value,self.layout[interval.high].value,
                               guard.span,self.context.text(guard.span),interval.inclusive,interval.length)

        statements=node.body.statements if isinstance(node.body,ast.Block) else [node.body]
        updates=[assignment(statement) for statement in statements]
        if "expansion" in self.features:
            result=self.growth(guard,updates,name)
            if result is not None:
                return result
        if "helper" in self.features:
            result=self.remainder(guard,updates,name)
            if result is not None:
                return result
        raise UnsupportedProjection

    def growth(self,guard,updates,name):
        if len(updates)!=1 or not isinstance(updates[0],ast.Assignment):
            return None
        node=updates[0]
        binding=self.index(node.target)
        expr=node.value
        if node.operator=="=" and isinstance(expr,ast.BinaryExpression) and expr.operator=="*" and self.index(expr.left)==binding:
            expr=expr.right
        elif node.operator!="*=":
            return None
        if not binding or not isinstance(expr,ast.Literal) or type(expr.value) is not int or not 2<=expr.value<=8:
            return None
        if not isinstance(guard,ast.BinaryExpression) or guard.operator!="&&":
            return None
        limit=guard.left
        if (not isinstance(limit,ast.BinaryExpression) or limit.operator!="<" or self.index(limit.left)!=binding
                or not isinstance(limit.right,ast.Literal)):
            return None
        reads=[part for part in walk(guard.right) if isinstance(part,ast.ArrayAccess) and self.index(part.index)==binding]
        if len(reads)!=1 or self.array_info(reads[0]) is None or not literal(limit.right,self.array_info(reads[0])[1]):
            return None
        self.expansions[name] = (binding,guard.span)
        return DynamicLoop("growth",self.layout[binding].value,None,guard.span,self.context.text(guard.span))

    def remainder(self,guard,updates,name):
        if (not isinstance(guard,ast.BinaryExpression) or guard.operator not in {"!=",">"} or not literal(guard.right,0)):
            return None
        binding=self.index(guard.left)
        targets=[node for node in updates if isinstance(node,ast.Assignment) and self.index(node.target)==binding]
        if not binding or len(targets)!=1 or targets[0].operator!="=":
            return None
        replacement=targets[0].value
        if isinstance(replacement,ast.Identifier):
            temporary=self.index(replacement)
            defs=[node for node in updates if isinstance(node,ast.VariableDeclaration) and self.bindings.declaration(node)==temporary]
            if len(defs)!=1:
                return None
            replacement=defs[0].initializer
        if not (isinstance(replacement,ast.BinaryExpression) and replacement.operator=="%" and self.index(replacement.right)==binding):
            return None
        self.modulo.add(name)
        return DynamicLoop("remainder",self.layout[binding].value,None,guard.span,self.context.text(guard.span))

    def handoff(self,item,interval):
        name=item.function.name
        growth,guard=self.expansions[name]
        if guard.start.offset>=interval.span.start.offset:
            return
        high=self.bindings.symbols[interval.high]
        for node in walk(item.function.body):
            if (isinstance(node,ast.VariableDeclaration) and node.span==high.declaration_span
                    and isinstance(node.initializer,ast.Identifier) and self.index(node.initializer)==growth):
                self.offsets[id(node.initializer)] = node.initializer.span
        if getattr(self,"sentinel",None) is None:
            return
        tail=item.function.body.statements[-1]
        if not isinstance(tail,ast.ReturnStatement) or not isinstance(tail.value,ast.BinaryExpression):
            return
        expr=tail.value
        if (expr.operator=="-" and isinstance(expr.left,ast.UnaryExpression)
                and expr.left.operator=="-" and self.index(expr.left.operand)==interval.low
                and literal(expr.right,-self.sentinel)):
            self.fallbacks[id(expr)] = self.sentinel

    def latch_transfer(self,node):
        return None if isinstance(node,ast.WhileStatement) else super().latch_transfer(node)


class Progress:
    depth_limit=8

    def __init__(self,model,changes=()):
        self.model=model
        self.strict=bool(changes)
        self.entry_guards={change.origin:change.value for change in changes if change.action=="entry_guard"}
        self.accesses={}
        self.frames={}

    def enter(self,name,values,parent):
        interval=self.model.recursive.get(name)
        if interval is None:
            return
        p,q=interval.positions
        lo,hi=values[p],values[q]
        observed=self.frames.setdefault(name,[])
        observed.append((lo,hi))
        if parent is None or parent[0]!=name:
            end=interval.length-int(interval.inclusive)
            if self.strict and hi-lo+int(interval.inclusive)>0 and not (0<=lo<interval.length and hi<=end):
                raise InvalidSample("SEARCH_ENTRY_OUTSIDE_EXTENT")
            return self.entry_guards.get(self.model.base_origins.get(name)) if hi<lo else None
        previous=parent[1]
        a,b=previous[p],previous[q]
        if not (a<=lo and hi<=b and (hi-lo)<(b-a) and
                all(value==previous[i] for i,value in enumerate(values) if i not in (p,q))):
            raise InvalidSample("SEARCH_INTERVAL_DID_NOT_SHRINK")
        return self.entry_guards.get(self.model.base_origins.get(name)) if hi<lo else None

    def measure(self,summary,facts):
        if not isinstance(summary,DynamicLoop):
            return None
        value=facts[summary.slot]
        if summary.mode=="interval":
            high=facts[summary.other]
            if (self.strict and high-value+int(summary.inclusive)>0
                    and not (0<=value<summary.extent and high<=summary.extent-int(summary.inclusive))):
                raise InvalidSample("SEARCH_ENTRY_OUTSIDE_EXTENT")
            return (value,high)
        return value

    def progress(self,summary,facts,previous):
        current=self.measure(summary,facts)
        if summary.mode=="interval":
            a,b=previous
            lo,hi=current
            valid=a<=lo and hi<=b and hi-lo<b-a
        elif summary.mode=="growth":
            valid=0<previous<current
        else:
            valid=abs(current)<abs(previous)
        if not valid:
            raise InvalidSample("DYNAMIC_PROGRESS_UNESTABLISHED")

    def cell(self,label,origin,index,length,initialized,mode):
        if origin is None:
            return
        if origin not in self.accesses:
            self.accesses[origin]={"function":label,"minimum":index,"maximum":index,
                                  "length":length,"initialized":True,"valid":True,"access":mode}
        row=self.accesses[origin]
        row["minimum"]=min(row["minimum"],index)
        row["maximum"]=max(row["maximum"],index)
        row["initialized"] &= initialized or mode=="write"
        row["valid"] &= 0<=index<length
