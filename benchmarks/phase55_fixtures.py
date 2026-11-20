"""Build the frozen, group-partitioned Phase 5.5 corpus from reviewed specifications."""
from collections import Counter
from hashlib import sha256
import json
from math import factorial, gcd, isqrt, prod
from pathlib import Path
import sys

PIN = "30507bbe41397065728167fb09aa820f9fce8dc7"
ROOT = Path(__file__).with_name("data") / "phase55"
UPSTREAM = "https://github.com/TheAlgorithms/Python"
ROWS = []


def pair(family, good, change, category, spec, inputs, oracle, upstream=None, partition="final", guidance=None):
    old, new = change
    assert good.count(old) == 1, family
    broken = good.replace(old, new)
    add(family, "control", good, category, spec, inputs, oracle, None, upstream, partition)
    add(family, "fault", broken, category, spec, inputs, oracle, good, upstream, partition, guidance)


def add(family, kind, source, category, spec, inputs, oracle, reference=None, upstream=None,
        partition="final", guidance=None):
    ROWS.append({
        "case_id": f"{family}-{kind}", "source_family": family,
        "source_origin": f"{UPSTREAM}/blob/{PIN}/{upstream}" if upstream else "Internally authored for Phase 5.5",
        "source_license": "MIT" if upstream else "No separate reuse license published",
        "adaptation_notes": ("Manually ported scalar behavior to bounded Mini-C. Faults were introduced for this study."
                             if upstream else "Written for an explicit local task or partial specification."),
        "mini_c_source": source, "program_validity": "compiler_valid" if "missing" not in source else "compiler_invalid",
        "fault_category": category, "is_known_correct": kind == "control", "is_ambiguous": kind == "ambiguous",
        "entry_point": "f", "input_vectors": inputs, "expected_outputs": [oracle(*v) for v in inputs],
        "reference_repairs": [reference] if reference else [], "acceptable_alternatives": [],
        "specification": spec, "guidance": guidance,
        "reviewer_notes": ("Expected values cover only the stated observations; intent remains partial." if kind == "ambiguous"
                           else "Reference justified by the task definition and independent fixture oracle."),
        "partition": partition, "origin_group": "external_adaptation" if upstream else "internal",
    })


def digit_total(n,b):
    if not n:
        return 0
    return n%b + digit_total(n//b,b)


pair("euclidean-remainder", "int f(int x,int y){while(y!=0){int next=x%y;x=y;y=next;}return x;}",
     ("next=x%y", "next=x/y"), "operator", "Compute the greatest common divisor for nonnegative integers.",
     [(21,14),(7,3),(0,8),(44,0)], gcd, "maths/greatest_common_divisor.py")
pair("decimal-digit-weight", "int f(int n){int s=0;while(n>0){s+=n%10;n/=10;}return s;}",
     ("s+=n%10","s+=n/10"), "operator", "Sum the decimal digits of a nonnegative integer.",
     [(0,),(9,),(315,),(9000,)], lambda n: sum(map(int,str(n))), "maths/sum_of_digits.py")
pair("root-bracket", "int f(int n){if(n<2){return n;}int lo=0;int hi=n/2;while(lo<=hi){int m=lo+(hi-lo)/2;int sq=m*m;if(sq==n){return m;}if(sq<n){lo=m+1;}else{hi=m-1;}}return hi;}",
     ("return hi;", "return lo;"), "return_dependency", "Return the floor of the square root for nonnegative bounded inputs.",
     [(1,),(9,),(19,),(625,)], isqrt, "maths/integer_square_root.py")
pair("factorial-product", "int f(int n){int p=1;while(n>1){p*=n;n--;}return p;}",
     ("p*=n", "p+=n"), "operator", "Return n factorial for 0 through 9.", [(0,),(1,),(4,),(8,)],
     factorial, "maths/factorial.py")
pair("stride-two-product", "int f(int n){if(n<=1){return 1;}return n*f(n-2);}",
     ("n*f(n-2)","n*f(n-1)"), "recurrence", "Multiply positive terms n, n-2, … through the same parity.",
     [(0,),(2,),(7,),(10,)], lambda n:prod(range(n,0,-2)), "maths/double_factorial.py",
     guidance={"return_expression":"n*f(n-2)","return_ordinal":2})
pair("hailstone-length", "int f(int n){int terms=1;while(n!=1){if(n%2==0){n/=2;}else{n=3*n+1;}terms++;}return terms;}",
     ("terms=1","terms=0"), "initialization", "Count the terms in the bounded hailstone sequence, including the starting value and 1.",
     [(1,),(2,),(4,),(11,),(31,)], {1:1,2:2,4:3,11:15,31:107}.__getitem__, "maths/collatz_sequence.py")
pair("modular-squaring", "int f(int b,int e,int m){int p=1%m;while(e>0){if(e%2==1){p=(p*b)%m;}e/=2;b=(b*b)%m;}return p;}",
     ("p=(p*b)%m","p=(p+b)%m"), "operator", "Compute base to exponent modulo a positive modulus on bounded inputs.",
     [(2,9,7),(7,0,11),(13,4,8),(2,4,1)], pow, "maths/modular_exponential.py")
pair("base-divisibility", "bool f(int n,int b){int x=n;int sum=0;while(x>0){sum+=x%b;x/=b;}return n%sum==0;}",
     ("return n%sum==0","return n%sum!=0"), "comparison", "Report if a positive number is divisible by its digit sum in base b.",
     [(18,10),(19,10),(9,2),(14,3)], lambda n,b: n % digit_total(n,b) == 0,
     "maths/special_numbers/harshad_numbers.py", guidance={"return_expression":"n%sum==0"})
pair("third-order-sequence", "int f(int n){if(n<2){return 0;}if(n==2){return 1;}int a=0;int b=0;int c=1;for(int i=3;i<=n;i++){int next=a+b+c;a=b;b=c;c=next;}return c;}",
     ("next=a+b+c", "next=b+c"), "recurrence", "Return term n of the sequence seeded 0, 0, 1 with three-term addition.",
     [(0,),(2,),(4,),(7,),(9,)], [0,0,1,1,2,4,7,13,24,44].__getitem__, "dynamic_programming/tribonacci.py")
pair("fibonacci-scalar", "int f(int n){if(n<2){return n;}return f(n-1)+f(n-2);}",
     ("if(n<2){return n;}","if(n<2){return 1;}"), "base_case", "Return term n of the sequence seeded 0, 1 with two-term addition.",
     [(0,),(1,),(4,),(8,)], [0,1,1,2,3,5,8,13,21].__getitem__, "maths/fibonacci.py")
pair("median-of-three", "int f(int a,int b,int c){if(a>b){int t=a;a=b;b=t;}if(b>c){int t=b;b=c;c=t;}if(a>b){return a;}return b;}",
     ("if(a>b){return a;}", "if(a>b){return c;}"), "return_dependency", "Return the middle of three signed inputs, allowing ties.",
     [(9,-1,3),(1,2,3),(9,9,1),(5,4,-3)], lambda *v:sorted(v)[1], "maths/average_median.py")



pair("invoice-net", "int f(int price,int quantity,int fee,int deposit){int total=0;total+=price;total+=quantity;total+=fee;total-=deposit;return total;}",
     ("return total;", "return fee;"), "return_dependency", "Sum charges and subtract the deposit.", [(3,4,8,2),(1,9,1,6)],
     lambda a,b,c,d:a+b+c-d, partition="development")
pair("opposing-bearing", "int angle(int a,int b){return b-a;}int f(int a,int b){int first=angle(a,b);int second=angle(a,b);int back=angle(b,a);return first+second+back;}",
     ("return first+second+back;", "return first+second-back;"), "argument_role_control",
     "Add two forward bearings and one reverse bearing.", [(1,8),(-3,3)], lambda a,b:b-a, partition="development")
pair("single-exit-meter", "int f(int n){int trips=0;for(int i=1;i<=n;trips++){return i+n;}return trips;}",
     ("return i+n;", "return i-n;"), "loop_early_exit", "Return n plus the first reading if a positive reading range exists.",
     [(0,),(2,),(7,)], lambda n:n+1 if n>0 else 0, partition="development")
pair("disabled-bank", "int f(bool use){int a[3];a[2]=8;if(false){return a[3];}if(use){return a[2];}return 0;}",
     ("a[2]=8","a[2]=5"), "unreachable_array", "Return 8 when enabled and zero otherwise.", [(True,),(False,)],
     lambda b:8 if b else 0, partition="development")
pair("packed-address", "int f(int row,int col){return row*17+col;}", ("row*17+col","row+17*col"), "arithmetic",
     "Return a row-major offset for width 17.", [(2,3),(0,10)], lambda a,b:17*a+b, partition="training")
pair("gift-boxes", "int f(int units){int width=7;return (units+width-1)/width;}", ("units+width-1","units"),
     "rounding", "Round unit demand up to whole boxes of seven.", [(0,),(3,),(14,),(15,)],
     lambda n:(n+6)//7, partition="calibration")
pair("lateral-window", "int f(int n){int stamp=0;int score=0;for(int j=2;j<n;j++){score+=j*2;}return score;}",
     ("j++){","stamp++){"), "loop_progress", "Sum even-numbered markers 2*j for j from 2 until n.",
     [(1,),(3,),(6,)], lambda n:sum(j*2 for j in range(2,n)), partition="selection")
pair("wrap-period", "int f(int reading,int period){while(reading>=period){reading-=period;}return reading;}",
     ("reading>=period","reading>period"), "comparison", "Wrap a positive-period reading to [0, period).",
     [(4,4),(28,5),(0,3)], lambda a,b:a%b, partition="selection")
pair("terminal-palette", "int f(int seed){int rgb[4];rgb[3]=seed*2;return rgb[3];}", ("return rgb[3]","return rgb[4]"),
     "array_edge", "Return the marker placed in the final palette cell.", [(1,),(7,)], lambda a:a*2)
pair("reconciliation", "int f(int credits,int carry,int rebate,int debits,int adjustment){int net=4;net+=credits;net+=carry;net-=debits;net+=rebate;net-=adjustment;return net;}",
     ("net=4","net=0"), "accumulator_control", "Start at four, add credits, carry and rebate, then subtract debits and the adjustment.",
     [(2,1,4,3,5),(7,5,1,0,5)], lambda a,b,c,d,e:4+a+b+c-d-e)
pair("three-direction-readings", "int d(int l,int r){return r-l;}int f(int base,int limit,bool flip){if(flip){return d(limit,base);}return d(base,limit)+d(base,limit);}",
     ("return d(limit,base);","return d(base,limit);"), "branch_roles", "Return a reverse reading in flip mode and two forward readings otherwise.",
     [(3,7,True),(3,7,False),(0,-2,True)], lambda a,b,t:a-b if t else 2*(b-a))
pair("marked-break", "int f(int size){int clock=0;int tally=0;for(int slot=0;slot<size;clock++){tally=slot+3;break;}return tally;}",
     ("tally=slot+3","tally=slot+2"), "loop_early_exit", "If the scan is nonempty, report its initial marker, 3.",
     [(0,),(1,),(5,)], lambda n:3 if n>0 else 0)
pair("independent-block-counter", "int f(int size){int tick=0;for(int slot=0;slot<size;tick++){{int tick=8;slot+=2;}}return tick;}",
     ("slot+=2","slot+=3"), "loop_body_progress", "Count visits when the loop body advances by two.",
     [(0,),(2,),(5,),(8,)], lambda n:(n+1)//2)
pair("dual-bank-guard", "int f(int n){int bank[2];bank[1]=n;if(false){return bank[2];}{int bank[4];bank[2]=7;return bank[2]+n;}}",
     ("bank[2]=7","bank[2]=8"), "unreachable_array", "Use a larger inner bank and return its marker plus the input.",
     [(1,),(3,),(-5,)], lambda n:7+n)
pair("difference-steps", "int f(int a,int b){return a-b;}", ("return a-b","return a+b"), "arithmetic",
     "Return the signed difference of the two readings.", [(2,7),(5,-1),(-1,0)], lambda a,b:a-b,
     guidance={"return_expression":"a-b"})
pair("antenna-displacement", "int d(int p,int q){return (q-p)*4;}int f(int start,int stop){return d(start,stop)+d(start,stop)+d(start,stop);}",
     ("+d(start,stop)+","+d(stop,start)+"), "argument_order", "Add three identical scaled forward displacement samples.",
     [(1,8),(-7,-2),(4,4)], lambda a,b:12*(b-a))
pair("signed-register", "int f(int w,int x,int y,int z){int r=2;{r+=w;r+=x;r+=y;r+=z;}if(r>40){return 40;}return r;}",
     ("r+=y","r-=y"), "accumulator_sign", "Add the four signed contributions, with a ceiling of 40.",
     [(2,-1,8,3),(10,10,10,10)], lambda *v:min(40,2+sum(v)))
pair("nested-marks", "int f(int level){int k=4;int s=0;if(level>0){for(int j=1;j<=level;j++){if(j%2==0){s+=j;}}}return s;}",
     ("j++){if","k++){if"), "loop_progress", "Sum even markers at or below the positive level.",
     [(0,),(4,),(7,)], lambda n:sum(range(2,n+1,2)))
add("optional-view", "ambiguous", "int f(int low,int high){return missing;}", "binding", "One observed sample has equal endpoints.",
    [(4,4)], lambda low,high:4)
add("balance-source", "ambiguous", "int f(int base,int target,int closing){return missing;}", "binding",
    "The only verified settlement has all readings equal.", [(9,9,9)], lambda *v:9)
add("coupled-valves", "ambiguous", "int f(bool enabled,int cold,int hot){if(!enabled){return 0;}return missing;}", "binding",
    "Only the disabled behavior is specified.", [(False,3,8)], lambda *v:0)
add("frame-offset", "ambiguous", "int f(int base,int shift){return base+shift;}", "arithmetic",
    "The zero-shift behavior alone was supplied.", [(3,0),(8,0)], lambda a,b:a)
add("opaque-rounding", "ambiguous", "int f(int x){return x/4;}", "rounding",
    "Only exact multiples of four have expectations.", [(8,),(12,)], lambda n:n//4)


def main(evidence):
    upstream = {row["source_origin"].split(f"/blob/{PIN}/")[1] for row in ROWS
                if row["origin_group"] == "external_adaptation"}
    pins = {path: sha256((evidence / Path(path).name).read_bytes()).hexdigest()
            for path in sorted(upstream | {"LICENSE.md", "searches/binary_search.py", "strings/hamming_distance.py",
                                          "maths/special_numbers/armstrong_numbers.py"})}
    payload = (json.dumps(ROWS, indent=2, ensure_ascii=False) + "\n").encode()
    (ROOT / "cases-v1.json").write_bytes(payload)
    manifest = {
        "version": 1, "sha256": sha256(payload).hexdigest(), "upstream": UPSTREAM, "revision": PIN,
        "upstream_sha256": pins,
        "quarantined_upstream": {"searches/binary_search.py": "Phase 3.5 binary search",
                                 "strings/hamming_distance.py": "Phase 3.5 Hamming distance",
                                 "maths/special_numbers/armstrong_numbers.py": "ML v3 Armstrong numbers"},
        "partitions": dict(sorted(Counter(row["partition"] for row in ROWS).items())),
    }
    (ROOT / "manifest-v1.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
