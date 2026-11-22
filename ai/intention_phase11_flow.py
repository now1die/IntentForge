"""Relational observations over the existing bounded typed CFG projection."""
from collections import defaultdict
from dataclasses import dataclass

from analysis_evidence.dataflow import effects
from compiler import ast_nodes as ast
from compiler.source_location import SourceSpan

from .intention_phase10_flow import DynamicLoop, assignment, literal, walk
from .intention_phase105_flow import EndpointProgress, EndpointProjection, Inspection
from .intention_phase95_flow import InvalidSample, Loop, contained
from .intention_phase9_loops import ORDER, step_expression


def binary(node, operator):
    return isinstance(node,ast.BinaryExpression) and node.operator==operator


def conjuncts(node):
    if binary(node,"&&"):
        return (*conjuncts(node.left),*conjuncts(node.right))
    return (node,)


@dataclass(frozen=True, slots=True)
class Interpolation:
    span: SourceSpan
    declaration: ast.VariableDeclaration
    low: str
    high: str
    key: str
    array: str
    extent: int
    values: tuple
    denominator: ast.BinaryExpression
    early_division: bool


class RelationalProjection(EndpointProjection):
    def __init__(self,context,program,enabled):
        super().__init__(context,program,digit_helpers="range" in enabled)
        self.relational_components = enabled
        self.interpolations = []
        self.linear_helpers = set()

    def return_statement(self,branch):
        if not isinstance(branch,ast.Block):
            return super().return_statement(branch)
        statements = branch.statements
        if not statements:
            return None
        for prefix in statements[:-1]:
            if not isinstance(prefix,ast.Block):
                return None
            # Nested-scope literals have no outer writes or externally visible
            # effects. Do not discard declarations in the return's own scope.
            if any(not isinstance(node,ast.Block) and not (
                   isinstance(node,ast.VariableDeclaration) and isinstance(node.initializer,ast.Literal))
                   and not isinstance(node,ast.Literal) for node in walk(prefix)):
                return None
        return self.return_statement(statements[-1])

    def return_refinement_span(self,branch):
        return self.return_statement(branch).span

    def loop_site(self,item,block,initializations):
        node = block.syntax
        if isinstance(node,ast.WhileStatement) and "interpolation" in self.relational_components:
            interpolation = self.interpolation(node)
            if interpolation is not None:
                self.interpolations.append(interpolation)
                return DynamicLoop("interpolation",self.layout[interpolation.low].value,self.layout[interpolation.high].value,
                                   interpolation.span,self.context.text(interpolation.span),True,interpolation.extent)
        if isinstance(node,ast.ForStatement) and "helper" in self.relational_components:
            repeated = self.assigned_induction(item,node)
            if repeated is not None:
                self.linear_helpers.add(item.function.name)
                return repeated
        return super().loop_site(item,block,initializations)

    def assigned_induction(self,item,node):
        initial = assignment(node.initializer)
        if not isinstance(initial,ast.Assignment) or initial.operator!="=":
            return None
        bound = node.condition
        key = self.index(initial.target)
        if key not in self.layout or self.index(initial.value)!=key or not isinstance(bound,ast.BinaryExpression):
            return None
        if bound.operator not in ORDER:
            return None
        condition = bound.operator
        limit = bound.right
        if self.index(bound.left)!=key:
            if self.index(bound.right)!=key:
                return None
            condition,limit = ORDER[condition],bound.left
        writes = set().union(*(effects(part.expression or part.syntax,self.bindings,conservative_calls=False).writes
                               for part in item.flow.graph.blocks if contained(node.body.span,part.syntax.span)))
        if key in writes or not isinstance(limit,ast.Literal) or type(limit.value) is not int or node.update is None:
            return None
        direction = 1 if condition in {"<","<="} else -1
        invariant = {name:term for name,term in self.layout.items() if name not in writes and name!=key}
        step_expression(self,key,node.update,invariant)
        return Loop(self.layout[key].value,direction,False,bound.span,condition,self.context.text(limit.span),
                    self.context.text(initial.value.span),self.context.text(node.update.span),())

    def interpolation(self,node):
        parts = conjuncts(node.condition)
        if len(parts)!=3:
            return None
        interval = next((part for part in parts if isinstance(part,ast.BinaryExpression)
                        and part.operator in {"<=",">="} and self.index(part.left) and self.index(part.right)),None)
        if interval is None:
            return None
        low,high = (self.index(part) for part in (interval.left,interval.right))
        if interval.operator==">=":
            low,high=high,low
        if low==high or low not in self.layout or high not in self.layout:
            return None
        endpoints = {}
        for test in parts:
            if test is interval or not isinstance(test,ast.BinaryExpression):
                continue
            left,right = test.left,test.right
            if isinstance(right,ast.ArrayAccess):
                left,right=right,left
                operator=ORDER.get(test.operator)
            else:
                operator=test.operator
            if not isinstance(left,ast.ArrayAccess) or not self.array_info(left) or not self.index(right):
                return None
            edge = self.index(left.index)
            if (edge,operator) not in {(low,"<="),(high,">=")}:
                return None
            endpoints[edge]=(self.array_info(left),self.index(right))
        if len(endpoints)!=2 or endpoints[low]!=endpoints[high]:
            return None
        (array,extent), key = endpoints[low]
        for declaration in walk(node.body):
            if not isinstance(declaration,ast.VariableDeclaration) or not binary(declaration.initializer,"+"):
                continue
            probe = declaration.initializer
            if self.index(probe.left)!=low:
                continue
            shape = self.probe_shape(probe.right,low,high,key,array)
            if shape:
                values,denominator,early = shape
                return Interpolation(node.condition.span,declaration,low,high,key,array,extent,values,denominator,early)
        return None

    def probe_shape(self,expression,low,high,key,array):
        early = binary(expression,"*") and binary(expression.left,"/")
        if early:
            divide = expression.left
            width,offset = divide.left,expression.right
        elif binary(expression,"/") and binary(expression.left,"*"):
            divide = expression
            width,offset = divide.left.left,divide.left.right
        else:
            return None
        denominator = divide.right
        if not all(binary(part,"-") for part in (width,offset,denominator)):
            return None
        if self.index(width.left)!=high or self.index(width.right)!=low or self.index(offset.left)!=key:
            return None
        upper,lower = denominator.left,denominator.right
        if not all(isinstance(node,ast.ArrayAccess) and self.array_info(node) and self.array_info(node)[0]==array
                   for node in (upper,lower,offset.right)):
            return None
        if (self.index(upper.index),self.index(lower.index),self.index(offset.right.index))!=(high,low,low):
            return None
        return (upper,lower,width,offset),denominator,early


class Trace(Inspection):
    def __init__(self,model):
        super().__init__(model)
        self.paths = defaultdict(list)
        self.calls = defaultdict(list)

    def branch(self,label,site,outcome):
        path = self.paths[label]
        if len(path)<32:
            path.append((site,outcome))

    def helper(self,label,arguments,result):
        rows = self.calls[label]
        fact = (arguments,result)
        if len(rows)<12 and fact not in rows:
            rows.append(fact)


class RelationalProgress(EndpointProgress):
    def __init__(self,model,*,strict=False):
        super().__init__(model,strict=strict)
        self.inspection = Trace(model)

    def measure(self,summary,facts):
        if isinstance(summary,DynamicLoop) and summary.mode=="interpolation":
            low,high = facts[summary.slot],facts[summary.other]
            if not 0<=low<=high<summary.extent:
                raise InvalidSample("INTERPOLATION_INTERVAL_OUTSIDE_EXTENT")
            return low,high
        return super().measure(summary,facts)

    def progress(self,summary,facts,previous):
        if isinstance(summary,DynamicLoop) and summary.mode=="interpolation":
            lo,hi=facts[summary.slot],facts[summary.other]
            if not (previous[0]<=lo and hi<=previous[1] and hi-lo<previous[1]-previous[0]):
                raise InvalidSample("INTERPOLATION_INTERVAL_DID_NOT_SHRINK")
            return
        super().progress(summary,facts,previous)
