"""Trusted, project-authored programs and independently checked expectations."""
from dataclasses import dataclass

from ai.behavior_oracle import ExecutionLimits, Status, Vector
from ai.intention_context import Example, Requirement


@dataclass(frozen=True)
class SemanticCase:
    family: str
    source: str
    vectors: tuple[Vector, ...]
    status: Status = Status.MATCHES_SUPPLIED_TESTS
    issue: str | None = None
    limits: ExecutionLimits = ExecutionLimits()


def vectors(*pairs):
    return tuple(Vector(arguments=args, expected=value) for args, value in pairs)


SEMANTICS = (
    SemanticCase("integer-arithmetic", "int f(int n){return (n*n-1)/3;}", vectors(((4,), 5), ((-7,), 16))),
    SemanticCase("comparison-short-circuit", "bool f(int n){return n==0 || (12/n>3);}", vectors(((0,), True), ((4,), False))),
    SemanticCase("nested-loop", "int f(int n){int s=0;for(int i=0;i<n;i++){for(int j=0;j<i;j++){s++;}}return s;}",
                 vectors(*(((n,), n*(n-1)//2) for n in range(9)))),
    SemanticCase("early-return", "int f(int n){while(n>0){if(n==3){return n;}n--;}return -1;}", vectors(((7,), 3), ((2,), -1))),
    SemanticCase("recursion", "int f(int n){if(n<=1){return n;}return f(n-2)+f(n-1);}", vectors(((8,), 21), ((6,), 8))),
    SemanticCase("array-update", "int f(){int a[3];a[0]=2;a[1]=a[0]++;a[2]=++a[0];return a[0]+a[1]+a[2];}", vectors(((), 10))),
    SemanticCase("global-reset", "int cache[4];int f(){cache[3]+=2;return cache[3];}", vectors(((), 2), ((), 2), ((), 2))),
    SemanticCase("lexical-shadowing", "int g=1;int read(){return g;}int f(){int g=3;{int g=4;g++;}return g+read();}", vectors(((), 4))),
    SemanticCase("divide-by-zero", "int f(int n){return 5%n;}", vectors(((0,), 0)), Status.BEHAVIOR_UNKNOWN, "DIVISION_BY_ZERO"),
    SemanticCase("array-outside-extent", "bool f(){bool marks[2];marks[2]=true;return false;}", vectors(((), False)),
                 Status.BEHAVIOR_UNKNOWN, "ARRAY_BOUNDS"),
    SemanticCase("bounded-loop", "int f(){int cursor=0;for(;;){cursor++;}}", vectors(((), 0)),
                 Status.EXECUTION_LIMITED, "STEP_LIMIT", ExecutionLimits(steps=40)),
    SemanticCase("bounded-storage", "int f(){int table[32];return 0;}", vectors(((), 0)),
                 Status.EXECUTION_LIMITED, "MEMORY_CELLS", ExecutionLimits(memory_cells=16)),
    SemanticCase("bounded-recursion", "int f(){return f();}", vectors(((), 0)),
                 Status.EXECUTION_LIMITED, "CALL_DEPTH", ExecutionLimits(call_depth=4)),
    SemanticCase("unsupported-type", "float g(){return 1.0;}int f(){return 2;}", vectors(((), 2)),
                 Status.EXECUTION_UNSUPPORTED, "UNSUPPORTED_CONSTRUCT"),
)


@dataclass(frozen=True)
class RepairCase:
    family: str
    source: str
    entry: str
    inputs: tuple[Vector, ...]
    accepted: str | None = None
    expression: str | None = None

    def requirement(self):
        return Requirement(function=self.entry, return_expression=self.expression,
                           examples=tuple(Example(row.arguments, row.expected) for row in self.inputs))


REPAIRS = (
    RepairCase("doubling-requirement", "int twice(int x){return x+2;}", "twice",
               vectors(((4,), 8), ((-3,), -6)), "int twice(int x){return x*2;}", "x * 2"),
    RepairCase("descending-array-bound", "int collect(){int a[5];int s=0;for(int i=3;i>=-1;i--){a[i]=i*2;s+=a[i];}return s;}", "collect",
               vectors(((), 12)), "int collect(){int a[5];int s=0;for(int i=3;i>-1;i--){a[i]=i*2;s+=a[i];}return s;}"),
    RepairCase("zero-divisor", "int quotient(int x){return x/(x-x);}", "quotient", vectors(((4,), 2), ((-6,), -3)),
               "int quotient(int x){return x/2;}", "x / 2"),
    RepairCase("coincident-arguments", "int choose(int opening,int closing){return missing;}", "choose", vectors(((9, 9), 9), ((1, 1), 1)),
               "int choose(int opening,int closing){return opening;}"),
    RepairCase("contradictory-specifications", "int next(int x){return x+1;}", "next", vectors(((8,), 9), ((0,), 1)),
               expression="x / (x - x)"),
    RepairCase("valid-global-control", "int saved=4;int pool(int x){saved+=x;return saved;}", "pool", vectors(((5,), 9), ((-3,), 1))),
    RepairCase("unavailable-float", "float scale(float x){return x+1.0;}int f(){return 3;}", "f", vectors(((), 3))),
)
