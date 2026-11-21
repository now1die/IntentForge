"""Freeze independently specified Mini-C programs and reviewed scalar domains."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from .phase65_fixtures import REVISION, UPSTREAM

ROOT = Path(__file__).with_name("phase7_data")
LICENSE = "LICENSE.md"
EXTERNAL = (
    "maths/digital_root.py", "maths/josephus_problem.py", "maths/special_numbers/automorphic_number.py",
    "maths/special_numbers/polygonal_numbers.py", "maths/manhattan_distance.py", "maths/sum_of_arithmetic_series.py",
)


def josephus(count, stride):
    circle = list(range(count))
    cursor = 0
    while len(circle) > 1:
        cursor = (cursor + stride - 1) % len(circle)
        circle.pop(cursor)
    return circle[0]


def fixtures():
    rows = []

    def add(family, source, args, expected, expectation, mutation=None, *, partition="final", external=None, requirement=None):
        origin = dict(group="external_adaptation" if external else "authored",
                      origin=f"{UPSTREAM}/blob/{REVISION}/{external}" if external else "IntentForge Phase 7",
                      license="MIT" if external else "repository license",
                      review="independent executable reference and internal adjudication")
        common = dict(family=family, partition=partition, provenance=origin, specification=expectation,
                      vectors=[dict(arguments=list(row), expected=expected(*row)) for row in args],
                      compiler_valid=True, requirement=requirement)
        if mutation:
            old, new = mutation
            assert source.count(old) == 1, family
            rows.append(dict(common, id=family+"-fault", source=source.replace(old, new),
                             disposition="fault", references=[source], fault_origin="project-injected"))
        rows.append(dict(common, id=family+"-control", source=source, references=[],
                         disposition="control" if mutation else "ambiguous", fault_origin=None))

    add("folded-offset", "int bump(int x){return x+5;}int f(int n,int a){if(n<=1){return a;}return bump(f(n-1,a));}",
        [(1,1),(2,4),(5,-7)], lambda n,a:a+5*max(n-1,0), "A fixed increment per recursive return.",
        ("bump(f(n-1,a))","bump(f(n,a))"), partition="development")
    add("clip-at-nineteen", "int f(int x){if(x>19){return 19;}return x;}",
        [(8,),(19,),(27,)],lambda x:min(x,19),"Cap at nineteen.",("x>19","x<19"),partition="selection")
    add("signed-midpoint", "int f(int a,int b){return a+(b-a)/2;}",
        [(4,8),(9,7),(-8,-2)],lambda a,b:a+int((b-a)/2),"Midpoint rounded toward the first endpoint.",
        ("(b-a)/2","(b-a)*2"),partition="calibration")

    add("josephus-ring", "int f(int people,int stride){if(people<=1){return 0;}return (f(people-1,stride)+stride)%people;}",
        [(1,4),(5,2),(7,4),(9,3)],josephus,"Zero-based survivor for positive small populations and strides.",
        ("f(people-1,stride)","f(people,stride)"),external=EXTERNAL[1])
    add("digital-root", "int f(int v){while(v>=10){int sum=0;while(v>0){sum+=v%10;v=v/10;}v=sum;}return v;}",
        [(0,),(8,),(388,),(4224,)],lambda v:0 if v==0 else 1+(v-1)%9,"Repeated decimal digit summation for nonnegative v.",
        ("v=v/10","v=v/9"),external=EXTERNAL[0])
    add("automorphic-tail", "bool f(int n){int power=10;int temp=n;while(temp>=10){power*=10;temp/=10;}return n*n%power==n;}",
        [(5,),(6,),(25,),(12,),(76,),(376,)],lambda n:str(n*n).endswith(str(n)),"Square ends in n's decimal digits.",
        ("temp/=10","temp/=100"),external=EXTERNAL[2])
    add("polygonal-layer", "int f(int index,int sides){return ((sides-2)*index*index-(sides-4)*index)/2;}",
        [(1,5),(4,3),(3,5),(5,6)],lambda n,s:sum(1+(s-2)*k for k in range(n)),"Count points in polygonal layers.",
        ("(sides-4)*index","(sides-3)*index"),external=EXTERNAL[3],
        requirement=dict(return_expression="((sides-2)*index*index-(sides-4)*index)/2"))
    add("manhattan-grid", "int gap(int x,int y){if(x>=y){return x-y;}return y-x;}int f(int a,int b,int c,int d){return gap(a,c)+gap(b,d);}",
        [(2,3,-1,3),(0,-7,2,-2),(-1,2,5,-8)],lambda a,b,c,d:abs(a-c)+abs(b-d),"Two-dimensional Manhattan distance.",
        ("gap(b,d)","gap(a,d)"),external=EXTERNAL[4])
    add("arithmetic-list", "int f(int a,int difference,int count){return count*(2*a+(count-1)*difference)/2;}",
        [(2,3,4),(5,-2,3),(-1,8,0),(-4,3,1)],lambda a,d,n:sum(a+k*d for k in range(n)),
        "Finite arithmetic list sum with nonnegative count.",("(count-1)*difference","count*difference"),external=EXTERNAL[5])
    add("recursive-doubler", "int lift(int value){return value*2;}int f(int remaining,int seed){if(remaining>0){return lift(f(remaining-1,seed));}return seed;}",
        [(0,7),(1,-3),(4,2)],lambda n,s:s*2**n,"Double once per positive remaining level.",
        ("lift(f(remaining-1,seed))","lift(f(remaining,seed))"))
    add("recursive-negator", "int sign(int x){return 0-x;}int pass(int x){return sign(x);}int f(int i,int token){if(i<5){return pass(f(i+1,token));}else{return token;}}",
        [(5,10),(4,6),(2,-8),(1,13)],lambda i,t:t*(-1)**max(5-i,0),"Alternate sign until index five.",
        ("pass(f(i+1,token))","pass(f(i,token))"))
    add("even-stride-total", "int f(int k,int total){if(k<=0){return total;}return f(k-2,total+k*k);}",
        [(0,9),(2,10),(4,-1),(6,0)],lambda k,t:t+sum(x*x for x in range(k,0,-2)),
        "Add only positive even-index squares over an even initial index.",("f(k-2,total+k*k)","f(k-1,total+k*k)"))
    add("projected-bias", "int bias(int x){return x+3;}int f(int x,int state){int raw=x+1;if(state>5){return bias(raw);}return raw;}",
        [(3,1),(3,6),(-5,9),(4,5)],lambda x,s:x+4 if s>5 else x+1,"Return a bias-corrected reading only above mode five.",
        ("return bias(raw);","return raw;"))
    add("threshold-history", "int f(int x,int mode){int first=x+11;int twice=first*2;int ready=twice+12;if(mode>=8){return ready;}return ready;}",
        [(4,0),(2,8),(5,12),(-4,7)],lambda x,m:2*(x+11)+12,"Return the final history reading on either side of the mode threshold.",
        ("if(mode>=8){return ready;}","if(mode>=8){return first;}"))
    add("bipolar-shaping", "int f(int x,int mode){int first=x-13;int square=first*first;int ready=square+2;if(mode<11){return first;}return ready;}",
        [(11,10),(8,11),(13,8),(25,14)],lambda x,m:x-13 if m<11 else (x-13)**2+2,"Return low-mode signed deviation and high-mode squared deviation.",
        ("if(mode<11){return first;}","if(mode<11){return ready;}"))
    add("lookup-weight", "int f(int n){if(n<=2){return 2;}return f(n-1)+f(n-3);}",
        [(2,),(3,),(5,),(7,)],lambda n:[2,2,2,4,6,8,12,18][n],"Add lag-one and lag-three terms with three seed values of two.",
        ("f(n-1)+f(n-3)","f(n-1)*f(n-3)"))
    add("biased-difference", "int f(int n){if(n<=3){return n+7;}return f(n-2)-f(n-4);}",
        [(3,),(4,),(6,),(9,)],lambda n:[7,8,9,10,2,2,-7,-8,-9,-10][n],
        "Subtract lag four from lag two using affine seeds.",("f(n-2)-f(n-4)","f(n-2)+f(n-4)"))
    add("wrapper-identity-terms", "int wrap(int row){return row;}int f(int n){if(n<=2){return n+1;}return wrap(f(n-1)*f(n-2));}",
        [(0,),(3,),(4,),(5,)],lambda n:[1,2,3,6,18,108][n],
        "Multiply two preceding terms after three distinct seeds.",("wrap(f(n-1)*f(n-2))","wrap(f(n-1)-f(n-2))"))
    add("medial-threshold", "int f(int n,int acc,int bias){if(n<3){return acc+bias;}else{{int n=7;}return f(n-1,acc+n,bias);}}",
        [(2,8,3),(3,0,7),(6,5,-2)],lambda n,a,b:a+b+sum(range(3,n+1)),"Sum descending levels and add an independent offset.",
        ("f(n-1,acc+n,bias)","f(n,acc+n,bias)"))
    add("integer-shelf", "int f(int stock,int reserved){if(stock>=reserved){return stock-reserved;}return 0;}",
        [(12,7),(3,9),(4,4),(11,0)],lambda s,r:max(s-r,0),"Only unreserved stock is available.",
        ("stock-reserved","stock+reserved"))
    add("triangular-account", "int f(int x){int previous=x*(x-1)/2;int next=previous+x;int scaled=next*5;return previous;}",
        [(0,),(5,),(12,)],lambda n:n*(n-1)//2,"Expose the previous triangular account balance.",
        ("return previous;","return scaled;"))
    add("slot-withdrawal", "int f(int i,int j,int amount){while(i<j){i+=2;amount-=3;}return amount;}",
        [(0,1,8),(3,10,25),(4,2,7)],lambda i,j,a:a-3*max(0,(j-i+1)//2),"Withdraw three units per two-position advance.",
        ("amount-=3","amount+=3"))
    add("remainder-increment", "int f(int value){if(value<0){return 0-value;}return value;}",
        [(0,),(3,),(-7,),(-24,)],abs,"Return scalar magnitude.",
        ("return 0-value;","return value;"),requirement=dict(description="Return the absolute value of value"))
    add("upper-inlet", "int f(int x,int y){if(x>=y){return x;}return y;}",
        [(5,1),(-3,-7),(0,0),(3,8)],max,"Return the greater inlet reading.",
        ("return x;","return y;"),requirement=dict(description="Return the maximum of x and y"))
    add("boolean-handoff", "bool f(bool a,bool b,bool enable){if(enable){return a;}return b;}",
        [(True,False,True),(False,True,True),(False,True,False)],lambda a,b,e:a if e else b,
        "Select active lane with a boolean switch.",("if(enable)","if(!enable)"),requirement=dict(condition="enable"))

    add("unspecified-peak", "int f(int base,int cap){if(base<=cap){return base;}return cap;}",
        [(2,7),(5,5)],min,"Only inputs before or at the cap were specified.")
    add("unspecified-progress", "int f(int count,int s){if(count<=2){return s;}return f(count-1,s+4);}",
        [(0,7),(2,4)],lambda n,s:s,"Only accumulator base values were specified.")
    add("sparse-stage", "int f(int a,int m){int initial=a+9;int next=initial+3;if(m>=6){return next;}return initial;}",
        [(2,0),(8,5)],lambda a,m:a+9,"The high-mode result is unspecified.")
    add("negative-zero-domain", "int f(int a){if(a<0){return -a;}return a+1;}",
        [(-3,),(-14,)],abs,"Only negative-input behavior was supplied.")
    add("partial-rectangle", "int f(int width,int depth){return width*depth;}",
        [(0,3),(4,0)],lambda w,d:0,"Only zero-area degenerate rectangles were specified.")
    add("partial-recurrence", "int f(int n){if(n<=6){return 4;}return f(n-2)-f(n-4);}",
        [(2,),(6,)],lambda n:4,"Only seed values are documented.")
    add("partial-clock", "int f(int t,bool reverse){if(reverse){return 12-t;}return t;}",
        [(2,False),(7,False)],lambda t,r:t,"Reverse-direction behavior was left open.")
    add("single-lane", "int f(int a,int b,int mode){if(mode==3){return a+b;}return a-b;}",
        [(4,5,3),(7,-2,3)],lambda a,b,m:a+b,"Only addition mode was specified.")
    add("empty-bucket", "int f(int x,int cap){if(x>=cap){return cap;}return x;}",
        [(0,0),(-1,0)],min,"Only an empty bucket was specified.")
    add("partially-ordered-levels", "int f(int lo,int hi){if(lo>=hi){return lo-hi;}return hi-lo;}",
        [(2,5),(-3,-1),(8,8)],lambda l,h:h-l,"Only nondecreasing endpoint pairs were specified.")
    return rows


def freeze():
    contents = fixtures()
    payload = (json.dumps(contents, indent=2, ensure_ascii=False)+"\n").encode()
    checksums = {path: sha256((ROOT/"upstream"/Path(path).name).read_bytes()).hexdigest()
                 for path in (LICENSE, *EXTERNAL)}
    manifest = dict(revision=REVISION, case_sha256=sha256(payload).hexdigest(), upstream_sha256=checksums,
                    partitions=dict(Counter(row["partition"] for row in contents)),
                    policy="Confirmed completed original mismatch; promote exactly one matching candidate; keep every compiled hypothesis visible. Deterministic static order.")
    (ROOT/"cases-v1.json").write_bytes(payload)
    (ROOT/"manifest-v1.json").write_text(json.dumps(manifest, indent=2)+"\n")


if __name__ == "__main__":
    freeze()
