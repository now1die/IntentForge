"""Freeze Phase 7.5 programs and independently computed discovery/holdout vectors."""
from collections import Counter
from hashlib import sha256
import json
from math import gcd
from pathlib import Path

from .phase65_fixtures import REVISION, UPSTREAM

ROOT = Path(__file__).with_name("phase75_data")
LICENSE = "LICENSE.md"
SOURCES = (
    "conversions/decimal_to_any.py", "maths/special_numbers/jacobsthal_number.py",
    "maths/series/geometric_series.py", "maths/special_numbers/hexagonal_number.py",
    "maths/padovan_sequence.py", "maths/eulers_totient.py",
)


def sequence(n, seeds, left, right, factor=1, combine=lambda a,b:a+b):
    series = list(seeds)
    while len(series) <= n:
        series.append(combine(series[-left], factor*series[-right]))
    return series[n]


def base_digits(n, base):
    digits = []
    while n:
        n, digit = divmod(n, base)
        digits.append(str(digit))
    return int("".join(reversed(digits))) if digits else 0


def fixtures():
    rows = []

    def add(family, text, domain, oracle, specification, mutation=None, *, partition="final", source=None,
            holdout=2, requirement=None):
        vectors = [{"arguments": list(args), "expected": oracle(*args)} for args in domain]
        training, hidden = (vectors[:-holdout],vectors[-holdout:]) if holdout else (vectors,[])
        assert training and not ({tuple(v["arguments"]) for v in training} & {tuple(v["arguments"]) for v in hidden}), family
        row = dict(family=family, partition=partition, compiler_valid=True, specification=specification,
                   vectors=training, holdout_vectors=hidden, requirement=requirement,
                   provenance={
                       "group":"external_adaptation" if source else "authored",
                       "origin":f"{UPSTREAM}/blob/{REVISION}/{source}" if source else "IntentForge Phase 7.5",
                       "license":"MIT" if source else "repository license",
                       "review":"independent arithmetic or executable reference, internally adjudicated",
                   })
        if mutation:
            old,new = mutation
            assert text.count(old)==1, family
            rows.append(dict(row,id=family+"-fault", source=text.replace(old,new), disposition="fault",
                             references=[text], fault_origin="project-injected"))
        rows.append(dict(row,id=family+"-control", source=text, references=[],
                         disposition="control" if mutation else "ambiguous", fault_origin=None))

    add("sequential-quarters", "int f(int n,int score){if(n<=2){return score;}int next=score+n;return f(n-4,next);}",
        [(2,1),(5,3),(12,-1),(10,2),(15,-4)],lambda n,s:s+sum(range(n,2,-4)),
        "Add sampled levels separated by four down to two.",("f(n-4,next)","f(n-1,next)"),partition="development")
    add("capped-depth", "int f(int x){if(x<17){return x;}return 17;}",
        [(2,),(17,),(99,),(-3,),(20,)],lambda x:min(x,17),"Return an upper capped sensor.",("x<17","x>17"),partition="selection")
    add("bitflag-choice", "bool f(bool first,bool second){if(first){return second;}return false;}",
        [(True,True),(True,False),(False,True),(False,False)],lambda x,y:x and y,"Conjunction over two flags.",
        ("return second;","return first;"),partition="calibration",holdout=1)

    add("septal-packing", "int f(int n){int place=1;int out=0;while(n>0){out=out+n%7*place;place*=10;n=n/7;}return out;}",
        [(0,),(11,),(67,),(221,),(44,),(103,),(777,)],lambda n:base_digits(n,7),
        "Pack base-seven representation into decimal digit positions for 0..777.",
        ("n=n/7","n=n/6"),source=SOURCES[0])
    add("weighted-jacobsthal", "int f(int n){if(n<=1){return n;}int prior=f(n-1);int weighted=2*f(n-2);return prior+weighted;}",
        [(0,),(3,),(5,),(8,),(6,),(9,)],lambda n:(2**n-(-1)**n)//3,
        "Jacobsthal terms with seeds 0, 1 and a weight of two on the lag-two term.",
        ("prior+weighted","prior-weighted"),source=SOURCES[1])
    add("geometric-remainder", "int f(int count,int ratio){if(count<=0){return 0;}return (1+ratio*f(count-1,ratio))%97;}",
        [(0,4),(4,2),(5,3),(6,4),(8,2),(7,5)],lambda n,r:sum(r**k for k in range(n))%97,
        "Sum a unit-seeded geometric progression, reported modulo 97.",
        ("f(count-1,ratio)","f(count,ratio)"),source=SOURCES[2])
    add("hexagonal-layer", "int f(int n){int span=2*n-1;return n*span;}",
        [(0,),(3,),(7,),(12,),(4,),(19,)],lambda n:sum(4*k+1 for k in range(n)),
        "Return hexagonal lattice count n(2n−1).",("2*n-1","2*n+1"),source=SOURCES[3],
        requirement=dict(return_expression="n*span"))
    add("padovan-through-local", "int carry(int x){int a=x;return a;}int f(int n){if(n<=2){return 1;}int a=f(n-2);int b=f(n-3);int mix=a+b;return carry(mix);}",
        [(1,),(4,),(7,),(9,),(8,),(11,)],lambda n:sequence(n,[1,1,1],2,3),
        "Padovan terms with seeds 1,1,1 and lags two and three.",("int mix=a+b","int mix=a*b"),source=SOURCES[4])
    add("coprime-count", "int gcd2(int a,int b){while(b>0){int r=a%b;a=b;b=r;}return a;}int f(int n){int total=0;for(int i=1;i<=n;i++){if(gcd2(n,i)==1){total++;}}return total;}",
        [(1,),(8,),(9,),(15,),(11,),(18,)],lambda n:sum(gcd(n,k)==1 for k in range(1,n+1)),
        "Count positive integers up to n coprime to n.",("gcd2(n,i)==1","gcd2(n,i)!=1"),source=SOURCES[5])

    add("parity-square-tally", "int f(int n,int a){if(n<2){return a;}int next=a+n*n;return f(n-2,next);}",
        [(0,1),(4,7),(6,0),(9,-3),(8,5),(5,10)],lambda n,s:s+sum(x*x for x in range(n,1,-2)),
        "Accumulate squares at every second level until below two.",("f(n-2,next)","f(n-1,next)"))
    add("descending-window", "int f(int index,int step,int accum){if(index<1){return accum;}return f(index-step,step,accum+2*index);}",
        [(0,2,9),(5,2,2),(11,3,7),(8,4,1),(13,5,-4),(7,2,3)],lambda i,s,a:a+sum(2*k for k in range(i,0,-s)),
        "Sample descending positive indices at the supplied positive stride.",("index-step","index-1"))
    add("rise-shot", "int f(int cursor,int step,int score){if(cursor>=12){return score;}return f(cursor+step,step,score+cursor*3);}",
        [(13,2,5),(2,3,1),(7,2,8),(0,4,7),(5,4,-3),(10,2,0)],lambda i,s,a:a+sum(3*k for k in range(i,12,s)),
        "Sum weighted ticks at the supplied positive stride up to twelve.",("cursor+step","cursor+2"))
    add("triple-attenuation", "int soften(int x){int local=x+2;int result=local/2;return result;}int f(int n,int value){if(n<=0){return value;}int recursive=f(n-3,value);return soften(recursive);}",
        [(0,10),(6,18),(9,33),(4,2),(13,50),(12,19)],lambda n,v:attenuate(n,v),
        "Apply a checked halving transform once per three units.",("f(n-3,value)","f(n-1,value)"))
    add("phase-wedge", "int f(int x,int state){int seed=x+4;int varying=seed*2;int result=varying+x;if(state>8){return result;}return result;}",
        [(1,5),(7,10),(-5,9),(4,8),(-7,12),(0,1)],lambda x,s:3*x+8,
        "Expose the composed wedge setting on each control path.",("if(state>8){return result;}","if(state>8){return seed;}"))
    add("dual-offset-grid", "int pixel(int u,int v){int mid=u*2;return mid+v;}int f(int a,int b,int c,int d){return pixel(a,c)+pixel(b,d);}",
        [(3,1,5,9),(3,4,5,9),(-2,1,2,8),(4,0,-3,8),(2,-5,7,2),(8,3,2,5)],lambda a,b,c,d:2*a+2*b+c+d,
        "Sum two weighted pair readings.",("pixel(b,d)","pixel(a,d)"))
    add("multiplicative-channels", "int channel(int x,int gain){return x+gain;}int f(int a,int b,int first,int second){return channel(a,first)*channel(b,second);}",
        [(2,1,3,7),(2,4,3,7),(1,2,0,8),(6,2,3,-1),(5,-3,2,7),(-3,4,0,5)],lambda a,b,u,v:(a+u)*(b+v),
        "Multiply independently composed channels.",("channel(b,second)","channel(a,second)"))
    add("clamped-helper-offset", "int clip(int x,int base){if(x>5){return 5+base;}return x+base;}int f(int a,int b,int low,int high){return clip(a,low)+clip(b,high);}",
        [(3,1,4,5),(3,4,4,5),(7,1,2,9),(1,8,7,2),(6,2,4,6),(0,3,-2,6)],lambda a,b,l,h:min(a,5)+min(b,5)+l+h,
        "Sum independently clipped channels and their offsets.",("clip(b,high)","clip(a,high)"))
    add("odd-radix-fold", "int f(int digits){int packed=1;while(digits>0){packed=packed*2+digits%5;digits/=5;}return packed;}",
        [(0,),(21,),(57,),(111,),(79,),(141,)],lambda n:fold_digits(n,5),
        "Fold base-five digits from low to high with binary weighting.",("digits/=5","digits/=4"))
    add("runtime-scale-count", "int f(int n){int steps=0;int scale=1;while(n>=8){scale*=8;steps+=scale;n/=8;}return steps;}",
        [(1,),(64,),(319,),(900,),(4096,),(4500,)],lambda n:sum(8**k for k in range(1,8) if n>=8**k),
        "Accumulate the powers of eight traversed during quotient reduction.",("n/=8","n/=16"))
    add("difference-lag-three", "int f(int n){if(n<=3){return n+3;}int newest=f(n-1);int old=f(n-4);return newest-old;}",
        [(1,),(5,),(7,),(9,),(8,),(11,)],lambda n:sequence(n,[3,4,5,6],1,4,combine=lambda a,b:a-b),
        "Subtract a lag-four value from the immediately previous term.",("newest-old","newest+old"))
    add("narrow-quadrature", "int f(int n){if(n<=3){return n+2;}int a=f(n-2);int b=f(n-3);return a*b;}",
        [(2,),(5,),(7,),(8,),(6,),(9,)],lambda n:sequence(n,[2,3,4,5],2,3,combine=lambda a,b:a*b),
        "Multiply distinct lag-two and lag-three terms.",("return a*b;","return a+b;"))
    add("forwarded-offset", "int shift(int local){int first=local+4;int scaled=first*2;return first;}int f(int a,int b){return shift(a)+b;}",
        [(2,4),(-4,7),(3,-1),(10,2),(6,0),(-2,1)],lambda a,b:a+b+4,
        "Keep the intermediate offset before scaling.",("return first;","return scaled;"))
    add("weighted-reserve", "int f(int stock,int reserve){int security=reserve*2;if(stock>security){return stock-security;}return 0;}",
        [(5,4),(10,2),(19,3),(9,4),(17,0),(3,6)],lambda x,y:max(x-2*y,0),
        "Reserve twice the per-unit requirement before releasing excess.",("stock-security","stock+security"))
    add("three-stage-counter", "int f(int x){int a=x-8;int b=a*3;int c=b-7;return c;}",
        [(1,),(8,),(13,),(-3,),(20,),(4,)],lambda x:3*(x-8)-7,
        "Return the fully adjusted calibrated stage.",("return c;","return a;"))
    add("rectangle-greater-edge", "int f(int a,int b){if(a>b){return a;}return b;}",
        [(1,7),(3,2),(-1,-3),(1,1),(2,9),(-2,7)],max,
        "Return the larger edge.",("if(a>b)","if(a<b)"),requirement=dict(condition="a>b",condition_ordinal=1))
    add("bisector-step", "int f(int u,int v){int r=u-v;int delta=r/2;return u-delta;}",
        [(3,1),(12,5),(-3,5),(7,7),(-8,-3),(24,-7)],lambda u,v:u-int((u-v)/2),
        "Move halfway toward v with division rounded toward zero.",("u-delta","u+delta"))
    add("two-flag-restoration", "bool f(bool r,bool s){if(r){return s;}return true;}",
        [(False,False),(True,False),(True,True),(False,True)],lambda r,s:not r or s,
        "Material implication from r to s.",("return true;","return false;"),holdout=1)
    add("squared-offset", "int f(int x){int bias=x+5;return bias*bias;}",
        [(0,),(5,),(-7,),(8,),(20,),(-3,)],lambda x:(x+5)**2,
        "Square the input after applying an offset of five.",("bias*bias","bias+x"),
        requirement=dict(description="Return the square of the shifted input"))

    add("sparse-interval", "int f(int a,int b,int carry){if(a>=b){return carry;}return f(a+2,b-1,carry+3);}",
        [(5,3,7),(4,4,2),(7,4,9)],lambda a,b,c:c,"Only finished intervals are specified.",holdout=0)
    add("unspecified-helper-fallback", "int h(int n){int previous=n-3;int adjusted=previous*2;return previous;}int f(int a,bool mode){if(mode){return h(a);}return a;}",
        [(1,False),(4,False),(-7,False)],lambda a,m:a,"Only the unadjusted mode is specified.",holdout=0)
    add("optional-nonunit-domain", "int f(int n,int p){if(n<=3){return p;}return f(n-3,p+2);}",
        [(1,5),(3,-1),(2,3)],lambda n,p:p,"Only the base domain has expected outputs.",holdout=0)
    add("partial-branched-product", "int f(int x,int y,int mode){if(mode==4){return x*y;}return x+y;}",
        [(1,7,4),(-2,5,4),(0,-5,4)],lambda x,y,m:x*y,"Only product mode is specified.",holdout=0)
    add("sparse-odd-base", "int f(int x){if(x<4){return 2;}int a=f(x-2);int b=f(x-3);return a-b;}",
        [(0,),(3,),(2,)],lambda x:2,"Only seed outputs are supplied.",holdout=0)
    add("partial-redistribution", "int f(int x,int y){if(x>=0){return x+2*y;}return y-x;}",
        [(2,4),(1,-7),(5,3)],lambda x,y:x+2*y,"Only nonnegative x was specified.",holdout=0)
    add("unset-carry", "int f(int n,int seed,int carry){if(n<2){return seed;}return f(n-2,seed+carry,carry);}",
        [(8,2,0),(10,-3,0),(5,4,0)],lambda n,s,c:s,"Expectations cover only zero carry.",holdout=0)
    add("partial-alarm", "bool f(int high,int low,bool armed){if(armed){return high>low+3;}return false;}",
        [(11,4,False),(-1,5,False),(3,1,False)],lambda x,y,a:False,"Only the disarmed state was supplied.",holdout=0)
    return rows


def attenuate(n, value):
    for _ in range((n+2)//3):
        value = (value+2)//2
    return value


def fold_digits(value, radix):
    result = 1
    while value:
        value, digit = divmod(value,radix)
        result = 2*result+digit
    return result


def freeze():
    cases=fixtures()
    payload=(json.dumps(cases,indent=2,ensure_ascii=False)+"\n").encode()
    hashes={path:sha256((ROOT/"upstream"/Path(path).name).read_bytes()).hexdigest() for path in (LICENSE,*SOURCES)}
    (ROOT/"cases-v1.json").write_bytes(payload)
    (ROOT/"manifest-v1.json").write_text(json.dumps(dict(
        revision=REVISION,case_sha256=sha256(payload).hexdigest(),upstream_sha256=hashes,
        partitions=dict(Counter(row["partition"] for row in cases)),
        selection_policy="Deterministic Phase 7 ranking and verified-original gate, fixed before final scoring. Holdout vectors never guide synthesis."
    ),indent=2)+"\n")


if __name__=="__main__":
    freeze()
