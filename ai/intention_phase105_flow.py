"""Checked endpoint, cell-relation and decreasing-digit observations."""
from dataclasses import dataclass

from compiler import ast_nodes as ast

from .intention_phase10_flow import DynamicLoop, Progress, SearchProjection, assignment, literal, walk
from .intention_phase95_flow import InvalidSample


@dataclass(frozen=True, slots=True)
class Relation:
    node: ast.BinaryExpression
    kind: str
    array: str
    cell_on_left: bool = True


class EndpointProjection(SearchProjection):
    def __init__(self, context, program, *, digit_helpers=False):
        super().__init__(context, program, frozenset({"search","expansion","helper"}))
        self.digit_helpers = digit_helpers
        self.relations = {}
        self.rotation_sites = set()
        self.digit_sites = {}
        self.nodes = {id(record.node):record.node for record in context.nodes}

    def interval_result(self,returned,interval):
        return (super().interval_result(returned,interval)
                or (not interval.inclusive and self.index(returned) in {interval.low,interval.high}))

    def prepare(self,name):
        super().prepare(name)
        function = self.functions[name].function
        for node in walk(function.body):
            if isinstance(node,ast.BinaryExpression) and node.operator in {"==","!=","<","<=",">",">="}:
                self.record_relation(node)

    def record_relation(self,node):
        left,right = node.left,node.right
        if isinstance(right,ast.ArrayAccess) and not isinstance(left,ast.ArrayAccess):
            left,right = right,left
        if not isinstance(left,ast.ArrayAccess):
            return
        array = self.array_info(left)
        if array is None:
            return
        if self.index(right) and self.index(left.index):
            self.relations[id(node)] = Relation(node,"key",array[0],left is node.left)
        elif isinstance(right,ast.ArrayAccess) and self.array_info(right)==array:
            first,second = (self.affine_index(part.index) for part in (left,right))
            if first is not None and second is not None and first[0]==second[0] and abs(first[1]-second[1])==1:
                self.relations[id(node)] = Relation(node,"neighbor",array[0])

    def affine_index(self,node):
        base = self.index(node)
        if base is not None:
            return base,0
        if isinstance(node,ast.Literal) and type(node.value) is int:
            return None,node.value
        if (isinstance(node,ast.BinaryExpression) and node.operator in {"+","-"}
                and self.index(node.left) and isinstance(node.right,ast.Literal) and type(node.right.value) is int):
            return self.index(node.left),node.right.value if node.operator=="+" else -node.right.value
        return None

    def halving(self,node,name):
        guard = node.condition
        if not isinstance(guard,ast.BinaryExpression) or guard.operator!="||":
            return None
        conditions = guard.left,guard.right
        if not all(isinstance(part,ast.BinaryExpression) and part.operator in {">","!="}
                   and literal(part.right,0) and self.index(part.left) in self.layout for part in conditions):
            return None
        keys = tuple(self.index(part.left) for part in conditions)
        body = node.body.statements if isinstance(node.body,ast.Block) else [node.body]
        if keys[0]==keys[1]:
            return None
        for key in keys:
            matches = [part for statement in body if isinstance((part:=assignment(statement)),ast.Assignment)
                       and self.index(part.target)==key]
            if len(matches)!=1:
                return None
            update = matches[0]
            if not (update.operator=="/=" and literal(update.value,2) or
                    update.operator=="=" and isinstance(update.value,ast.BinaryExpression)
                    and update.value.operator=="/" and self.index(update.value.left)==key and literal(update.value.right,2)):
                return None
        self.digit_sites[name] = node.span
        left,right = (self.layout[key].value for key in keys)
        return DynamicLoop("halving",left,right,guard.span,self.context.text(guard.span))

    def neighbor_scan(self,node):
        guard = node.condition
        if not isinstance(guard,ast.BinaryExpression) or guard.operator!="&&":
            return None
        bound,check = guard.left,guard.right
        body = node.body.statements if isinstance(node.body,ast.Block) else [node.body]
        if len(body)!=1 or not isinstance((update:=assignment(body[0])),ast.UpdateExpression):
            return None
        key = self.index(update.operand)
        if not (key in self.layout and isinstance(bound,ast.BinaryExpression) and self.index(bound.left)==key
                and isinstance(check,ast.BinaryExpression) and check.operator=="=="
                and isinstance(check.left,ast.ArrayAccess) and self.array_info(check.left) and self.index(check.right)):
            return None
        length = self.array_info(check.left)[1]
        direction = -1 if update.operator=="--" else 1
        if (bound.operator!=(">" if direction<0 else "<") or not literal(bound.right,0 if direction<0 else length-1)
                or self.affine_index(check.left.index)!=(key,direction)):
            return None
        return DynamicLoop("neighbor_scan",self.layout[key].value,direction,guard.span,self.context.text(guard.span))

    def loop_site(self,item,block,initializations):
        node = block.syntax
        if isinstance(node,ast.WhileStatement):
            scan = self.neighbor_scan(node)
            if scan is not None:
                return scan
        if isinstance(node,ast.WhileStatement) and self.digit_helpers:
            shrinking = self.halving(node,item.function.name)
            if shrinking is not None:
                return shrinking
        result = super().loop_site(item,block,initializations)
        if isinstance(node,ast.WhileStatement) and isinstance(result,DynamicLoop) and result.mode=="interval":
            interval = self.intervals[item.function.name][-1]
            for expr in walk(node.body):
                if not isinstance(expr,ast.BinaryExpression) or expr.operator not in {"<","<=",">",">="}:
                    continue
                left,right = expr.left,expr.right
                if isinstance(left,ast.ArrayAccess) and isinstance(right,ast.ArrayAccess):
                    if (self.array_info(left) is not None and self.array_info(left)==self.array_info(right)
                            and {self.index(left.index),self.index(right.index)}=={interval.midpoint,interval.high}):
                        self.relations[id(expr)] = Relation(expr,"rotation",self.array_info(left)[0])
                        self.rotation_sites.add(id(expr))
        return result


class EndpointProgress(Progress):
    def __init__(self,model,*,strict=False):
        super().__init__(model)
        self.strict = strict
        self.inspection = Inspection(model)

    def measure(self,summary,facts):
        if isinstance(summary,DynamicLoop) and summary.mode=="halving":
            values = facts[summary.slot],facts[summary.other]
            if min(values)<0:
                raise InvalidSample("DIGIT_INPUT_OUTSIDE_NONNEGATIVE_DOMAIN")
            return values
        return super().measure(summary,facts)

    def progress(self,summary,facts,previous):
        if summary.mode=="halving":
            if self.measure(summary,facts)!=tuple(value//2 for value in previous):
                raise InvalidSample("DIGIT_PROGRESS_UNESTABLISHED")
        elif summary.mode=="neighbor_scan":
            if self.measure(summary,facts)-previous!=summary.other:
                raise InvalidSample("NEIGHBOR_PROGRESS_UNESTABLISHED")
        else:
            super().progress(summary,facts,previous)


class Inspection:
    """Bounded facts from actual comparisons and checked array reads."""
    def __init__(self,model):
        self.model = model
        self.reads = {}
        self.relations = {}
        self.faults = []

    def read(self,label,origin,index,value,cells):
        self.reads[origin] = index,value,cells

    def fault(self,term,operation,left,right):
        self.faults.append((term.origin,operation,left,right))

    def helper(self,label,arguments,result):
        pass

    def branch(self,label,site,outcome):
        pass

    def compare(self,term,operation,left,right):
        relation = self.model.relations.get(term.origin)
        if relation is None:
            return
        node = relation.node
        cell = node.left if relation.cell_on_left else node.right
        read = self.reads.get(id(cell))
        if read is None:
            return
        index,_,cells = read
        other = self.reads.get(id(node.right)) if relation.kind!="key" else None
        value = right if relation.cell_on_left else left
        sample = (index, left, right, cells, other[0] if other else None, value)
        facts = self.relations.setdefault(term.origin,[])
        if len(facts)<8 and sample not in facts:
            facts.append(sample)
