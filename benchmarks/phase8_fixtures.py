"""Freeze independently specified Phase 8 arithmetic and control families."""
from collections import Counter
from hashlib import sha256
from itertools import product
import json
from math import prod
from pathlib import Path

from .phase65_fixtures import REVISION, UPSTREAM

ROOT = Path(__file__).with_name("phase8_data")
LICENSE = "LICENSE.md"
SOURCES = (
    "maths/volume.py", "conversions/temperature_conversions.py", "financial/price_plus_tax.py",
    "maths/shoelace_area.py", "maths/special_numbers/pronic_number.py", "maths/polynomial_evaluation.py",
    "maths/series/arithmetic.py", "conversions/time_conversions.py", "maths/special_numbers/triangular_numbers.py",
)


def trunc(numerator, denominator):
    return (-1 if numerator < 0 else 1)*(abs(numerator)//denominator)


def fixtures():
    rows = []

    def add(family, source, samples, reference, spec, mutation=None, *, external=None,
            partition="final", holdout=2, requirement=None, domain="Listed bounded integer samples and the stated mathematical domain"):
        vectors=[dict(arguments=list(args),expected=reference(*args)) for args in samples]
        split=len(vectors)-holdout
        discovery, hidden=vectors[:split], vectors[split:]
        assert discovery and not ({tuple(v["arguments"]) for v in discovery} & {tuple(v["arguments"]) for v in hidden}), family
        common=dict(family=family, partition=partition, compiler_valid=True,specification=spec,
                    vectors=discovery,holdout_vectors=hidden,requirement=requirement,domain=domain,
                    provenance=dict(group="external_adaptation" if external else "authored",
                                    origin=f"{UPSTREAM}/blob/{REVISION}/{external}" if external else "IntentForge Phase 8",
                                    license="MIT" if external else "repository license",
                                    upstream_revision=REVISION if external else None,
                                    review="independent executable reference and internal adjudication"))
        if mutation:
            old,new=mutation
            assert source.count(old)==1, family
            rows.append(dict(common,id=family+"-fault",source=source.replace(old,new),
                             references=[source],disposition="fault",fault_origin="project-injected"))
        rows.append(dict(common,id=family+"-control",source=source,references=[],fault_origin=None,
                         disposition="control" if mutation else "ambiguous"))

    add("biased-reading", "int f(int x){return 11*x-7;}", [(-2,),(0,),(3,),(4,),(-8,)],
        lambda x:sum([x]*11)-7,"Apply gain eleven and then remove seven.",("11*x","12*x"),partition="development")
    add("selection-box", "int f(int u,int v){return (u+5)*(v-3);}", [(2,0),(1,4),(5,9),(-2,6),(4,-1)],
        lambda u,v:prod([u+5,v-3]),"Area of signed translated edges.",("v-3","v-4"),partition="selection")
    add("calibration-shortage", "int f(int value,int limit){if(value<limit){return limit-value;}return 0;}",
        [(2,7),(1,0),(-8,8),(3,3),(98,2)],lambda a,b:max(b-a,0),
        "Measure shortage against limit.",("limit-value","limit+value"),partition="calibration")

    add("square-pyramid-volume", "int f(int side,int height){int footprint=side*side;return footprint*height/3;}",
        [(1,3),(3,7),(8,2),(2,16),(14,15),(17,13)],lambda a,h:sum([a*a]*h)//3,
        "Return integer square pyramid volume for nonnegative dimensions.",("height/3","height/2"),external=SOURCES[0])
    add("celsius-integer-fahrenheit", "int f(int c){int scale=9*c;return scale/5+32;}",
        [(-40,),(0,),(17,),(53,),(-18,),(100,)],lambda c:32+trunc(sum([c]*9),5),
        "Convert Celsius with signed integer truncation before offset.",("scale/5+32","scale/5+31"),external=SOURCES[1])
    add("integer-tax-total", "int f(int subtotal,int tenths){int levy=subtotal*tenths/10;return subtotal+levy;}",
        [(1,0),(25,2),(101,7),(78,1),(210,3),(37,4)],lambda x,t:x+sum([x]*t)//10,
        "Add a tax rate measured in tenths to a nonnegative subtotal.",("subtotal+levy","subtotal-levy"),external=SOURCES[2])
    add("oriented-shoelace", "int f(int a,int b,int c,int d,int e,int g){int positive=a*d+c*g+e*b;int negative=b*c+d*e+g*a;return (positive-negative)/2;}",
        [(1,2,7,3,1,8),(0,0,5,0,0,7),(2,3,9,6,3,9),(5,1,8,8,1,7),(-3,-1,7,2,0,9),(9,0,12,9,-1,3)],
        lambda a,b,c,d,e,g:((c-a)*(g-b)-(d-b)*(e-a))//2,
        "Truncated signed shoelace area of the listed counterclockwise triangles.",("positive-negative","positive+negative"),external=SOURCES[3])
    add("pronic-enumerator", "int f(int layer){return layer*(layer+1);}",
        [(0,),(3,),(7,),(12,),(5,),(31,)],lambda n:2*sum(range(1,n+1)),
        "Return the nth nonnegative pronic number.",("layer*(layer+1)","layer*layer"),external=SOURCES[4])
    add("signed-horner-quadratic", "int f(int x,int lead,int middle,int tail){int prior=lead*x+middle;return prior*x+tail;}",
        [(-3,2,5,7),(1,7,5,-2),(3,-2,7,1),(7,5,-1,6),(0,4,2,8),(11,1,3,6)],
        lambda x,p,q,r:p*x**2+q*x+r,"Evaluate independently supplied quadratic coefficients.",
        ("lead*x+middle","lead*x-middle"),external=SOURCES[5])
    add("one-based-series-term", "int f(int first,int position,int difference){return first+(position-1)*difference;}",
        [(4,1,7),(3,2,6),(-5,4,2),(9,8,-3),(6,13,5),(15,11,-4)],
        lambda f,n,d:list(f+d*i for i in range(n))[-1],
        "One-based arithmetic progression term.",("(position-1)*difference","position*difference"),external=SOURCES[6])
    add("minute-seconds", "int minutes(int n){return n*60;}int f(int m,int s){return minutes(m)+s;}",
        [(0,3),(1,17),(3,49),(21,2),(29,27),(55,59)],lambda m,s:sum((m*30,m*30,s)),
        "Convert whole minutes and residual seconds to seconds.",("n*60","n*61"),external=SOURCES[7])
    add("triangular-edge", "int f(int n){return n*(n+1)/2;}",
        [(1,),(4,),(5,),(16,),(9,),(31,)],lambda n:sum(range(n+1)),
        "Sum the first n nonnegative integer levels.",("n*(n+1)","n*(n-1)"),external=SOURCES[8])

    add("paired-dial", "int f(int x,int y){return (x+1)*(y+2);}",[(4,2),(6,4),(8,6),(10,8),(3,7),(-1,5)],
        lambda x,y:prod([x+1,y+2]),"Multiply independently shifted dial readings.",("y+2","y+3"),
        domain="Discovery follows x=y+2. Held-out signed pairs independently vary the two dials.")
    add("finite-grid", "int f(int row,int column){return (row+1)*(3*column+1);}",
        [(0,0),(0,2),(2,1)]+[(a,b) for a,b in product(range(3),repeat=2) if (a,b) not in {(0,0),(0,2),(2,1)}],
        lambda a,b:sum([3*b+1]*(a+1)),"Evaluate the cell weight for the 0..2 by 0..2 finite grid.",
        ("3*column","4*column"),holdout=6,domain="Exhaustive pairs (row,column) in {0,1,2} × {0,1,2}, split 3/6.")
    add("checked-offset-edge", "int f(int x){return x+3;}",
        [(3,),(-7,),(53,),(0,),(2147483644,),(-2147483648,)],lambda x:x+3,
        "Add three inside the checked int32 result domain.",("x+3","x+2"),
        domain="Inputs from INT_MIN through INT_MAX−3, including both endpoints on holdout.")
    add("difference-of-scaled-stages", "int reduce(int z){int scaled=3*z;int adjustment=scaled+4;return adjustment;}int f(int a,int b){return reduce(a)-b;}",
        [(1,2),(-5,7),(9,0),(5,-6),(8,3),(-4,-2)],lambda a,b:sum([a]*3)+4-b,
        "Remove baseline after helper scaling and offset.",("return adjustment;","return scaled;"))
    add("second-stage-source", "int f(int x,int y){int raw=x+2;int adjusted=raw*3+y;int label=adjusted+17;return adjusted;}",
        [(4,3),(-1,-2),(7,5),(1,23),(-8,-4),(55,6)],lambda a,b:3*a+6+b,
        "Keep the adjusted value while computing a separate label.",("return adjusted;","return label;"))
    add("one-argument-wrapper", "int origin(int n){int tick=n-1;return tick;}int scale(int n){int offset=origin(n);return offset*4;}int f(int position,int start){return start+scale(position);}",
        [(4,3),(1,7),(7,-3),(9,6),(5,11),(23,-9)],lambda n,a:a+sum([4]*(n-1)),
        "Use the one-based wrapper count to produce a signed offset.",("int tick=n-1","int tick=n+1"))
    add("signed-sampling-remainder", "int f(int signal,int period){int adjusted=signal-5;return adjusted%period;}",
        [(15,3),(-7,5),(26,7),(2,4),(-100,9),(121,11)],
        lambda a,b:(a-5)-trunc(a-5,b)*b,"Return Mini-C signed remainder after bias removal.",("adjusted%period","adjusted/period"),
        domain="Supported small signed inputs and positive nonzero periods.")
    add("successor-product", "int f(int code,int delta){int adjustment=code*2;return (adjustment+1)*delta;}",
        [(4,7),(1,-7),(7,2),(-4,9),(8,-9),(-3,-8)],lambda a,b:2*a*b+b,
        "Scale the next adjusted position.",("(adjustment+1)*delta","adjustment*delta"))
    add("throttled-sum", "int f(int work,int slices){return (work+2)*(slices-1);}",
        [(0,4),(7,2),(5,7),(-2,8),(15,4),(3,14)],lambda w,s:sum([w+2]*(s-1)),
        "Count the gaps between positive slice positions.",("(slices-1)","slices"))
    add("triad-overlap", "int f(int a,int b,int c){int merged=a+b;int removed=b+c;return merged*removed;}",
        [(2,3,1),(8,0,9),(3,4,7),(5,-1,1),(-3,-1,-2),(4,11,7)],lambda a,b,c:a*b+a*c+b*b+b*c,
        "Multiply the two overlapping adjacent totals.",("merged*removed","merged/removed"))
    add("subtraction-interaction", "int step(int x,int y){int offset=y-2;return x*offset;}int f(int a,int b,int base){return step(a,b)-base;}",
        [(5,4,6),(7,3,3),(2,8,-4),(12,-1,9),(8,7,0),(-2,6,13)],lambda a,b,c:a*b-2*a-c,
        "Scale the adjusted helper input and subtract the base.",("y-2","y-1"))
    add("three-window-divisor", "int f(int n){int span=n-6;return span/3+7;}",
        [(8,),(22,),(-3,),(61,),(0,),(-46,)],lambda n:trunc(n-6,3)+7,
        "Truncate the offset window in units of three.",("span/3","span/4"))
    add("two-independent-coefficients", "int f(int a,int b){return 5*a+7*b;}",
        [(0,3),(3,0),(4,7),(9,-2),(11,3),(-4,-7)],lambda a,b:sum([a]*5+[b]*7),
        "Apply five and seven to independent inputs.",("5*a+7*b","4*a+8*b"))
    add("coupled-index-recurrence", "int f(int x,int y,int total){if(x>=y){return total;}return f(x+2,y-1,total+x+y);}",
        [(0,5,7),(1,3,4),(2,10,0),(7,5,1),(0,15,-3),(2,11,5)],
        lambda x,y,n:n+(x+y)*turns(x,y)+turns(x,y)*(turns(x,y)-1)//2,
        "Close an interval by advancing the left edge twice per decrement of the right edge.",
        ("f(x+2,y-1","f(x+2,y+1"))
    add("rare-upper-adjustment", "int f(int x,int mode){if(mode>12){return x*3+4;}return x+4;}",
        [(3,0),(5,14),(6,4),(-4,15),(17,12),(-2,17)],lambda x,m:3*x+4 if m>12 else x+4,
        "Triple only on the high mode branch.",("x*3+4","x*4+4"),requirement=dict(return_expression="x*3+4",return_ordinal=1))
    add("counted-even-threshold", "int f(int n){int count=0;for(int i=0;i<n;i++){if(i%2==0){count++;}}return count;}",
        [(0,),(1,),(5,),(8,),(10,),(13,)],lambda n:len(range(0,n,2)),
        "Count even integer members below n.",("i%2==0","i%2==1"))
    add("boolean-active-window", "bool f(int x,int start,int stop){return x>=start&&x<stop;}",
        [(2,2,6),(6,2,6),(1,2,6),(4,2,6),(-3,-3,3),(12,5,12)],lambda x,a,b:a<=x<b,
        "Return membership in a half-open active window.",("x<stop","x<=stop"))
    add("clear-baseline", "int f(int x,int y){if(x>=y){return x;}return y;}",
        [(2,-1),(1,4),(-3,-8),(1,1),(0,8),(4,-3)],max,
        "Choose the greater measurement.",("x>=y","x<=y"),requirement=dict(description="Return the maximum of x and y"))

    add("coincident-shifts", "int f(int a,int b){return (a-3)*b;}",[(4,0),(9,0),(-3,0)],
        lambda a,b:0,"Only zero-width observations are specified.",holdout=0)
    add("partial-offset", "int f(int seed,int n){return seed+(n+8)*3;}",[(2,-8),(7,-8),(-2,-8)],
        lambda s,n:s,"Only the neutral position was specified.",holdout=0)
    add("same-position-distance", "int f(int a,int b){int step=b-a;return step*step;}",[(1,1),(6,6),(-7,-7)],
        lambda a,b:0,"Only identical endpoints were specified.",holdout=0)
    add("unsigned-mode", "int f(int x,bool signedMode){if(signedMode){return -x;}return x;}",[(9,False),(3,False),(-8,False)],
        lambda x,m:x,"Signed mode was left unspecified.",holdout=0)
    add("zero-progress-cases", "int f(int n,int carry){if(n<=3){return carry;}return f(n-2,carry+n);}",[(0,4),(3,-3),(1,9)],
        lambda n,c:c,"Only the three base inputs constrain behavior.",holdout=0)
    add("idle-item-charge", "int f(int count,int price){return count*(price-1);}",[(0,6),(0,7),(0,19)],
        lambda c,p:0,"Only invoices without units are specified.",holdout=0)
    add("unchecked-branch-label", "int f(int a,int m){if(m==5){return a*2;}return a+2;}",[(7,5),(-4,5),(2,5)],
        lambda x,m:x*2,"Only mode five was supplied.",holdout=0)
    return rows


def turns(x,y):
    return max(0,(y-x+2)//3)


def freeze():
    cases=fixtures()
    payload=(json.dumps(cases,indent=2,ensure_ascii=False)+"\n").encode()
    hashes={p:sha256((ROOT/"upstream"/Path(p).name).read_bytes()).hexdigest() for p in (LICENSE,*SOURCES)}
    (ROOT/"cases-v1.json").write_bytes(payload)
    (ROOT/"manifest-v1.json").write_text(json.dumps(dict(
        revision=REVISION,case_sha256=sha256(payload).hexdigest(),upstream_sha256=hashes,
        partitions=dict(Counter(row["partition"] for row in cases)),
        selection_policy="Checked scalar grammar, four proposals and deterministic ranking frozen before scoring; collapse optional suggestions for matching originals."
    ),indent=2)+"\n")


if __name__=="__main__":
    freeze()
