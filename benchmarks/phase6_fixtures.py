"""Recreate the versioned Mini-C corpus from fixed, independent specifications."""
from collections import Counter
from hashlib import sha256
import json
from math import comb, factorial
from pathlib import Path
import sys

ROOT = Path(__file__).with_name("data") / "phase6"
REVISION = "30507bbe41397065728167fb09aa820f9fce8dc7"
ORIGIN = "https://github.com/TheAlgorithms/Python"
CASES = []


def add(family, disposition, code, category, specification, inputs, oracle, *, reference=None, upstream=None,
        partition="final", compiler_valid=True):
    CASES.append({
        "id": f"{family}-{disposition}", "family": family, "partition": partition,
        "disposition": disposition, "category": category, "source": code, "compiler_valid": compiler_valid,
        "entry": "f", "specification": specification,
        "references": [reference] if reference else [],
        "vectors": [{"arguments": list(args), "expected": oracle(*args)} for args in inputs],
        "provenance": {"group": "external_adaptation" if upstream else "internal",
                       "origin": f"{ORIGIN}/blob/{REVISION}/{upstream}" if upstream else "Project-authored Phase 6 fixture",
                       "license": "MIT" if upstream else "No separate reuse license published",
                       "adaptation": "Scalar Mini-C port and injected defect; separate reference oracle." if upstream
                       else "Separately specified Mini-C example with arithmetic or reviewed expected values."},
    })


def pair(family, good, mutation, category, specification, inputs, oracle, **metadata):
    original, changed = mutation
    assert good.count(original) == 1, family
    add(family, "control", good, category, specification, inputs, oracle, **metadata)
    add(family, "fault", good.replace(original, changed), category, specification, inputs, oracle, reference=good, **metadata)


pair("proper-divisor-total", "int f(int n){int total=0;int visits=0;if(n<=1){return 0;}for(int d=1;n>d;d++){if(n%d==0){total+=d;}}return total;}",
     ("n>d;d++","n>d;visits++"), "loop_progress", "Sum positive proper divisors of a positive integer.",
     [(1,),(6,),(12,),(17,)], lambda n:sum(x for x in range(1,n) if n%x==0), upstream="maths/aliquot_sum.py")
pair("fixed-point-horner", "int f(int coefficient){int head=7+coefficient;int folded=head*2;int value=folded*2-5;return value;}",
     ("return value","return head"), "return_dependency", "Evaluate Horner's polynomial with head coefficient 7+coefficient, then two doublings and a terminal -5.",
     [(0,),(3,),(-8,),(20,)], lambda k:4*(7+k)-5, upstream="maths/polynomial_evaluation.py")
pair("scaled-geometric-total", "int f(int n){if(n<=0){return 0;}return 4*f(n-1)+3;}",
     ("4*f(n-1)","4*f(n)"), "recursive_progress", "Sum the first n positive terms of ratio four and initial term three.",
     [(0,),(1,),(3,),(5,)], lambda n:4**n-1, upstream="maths/sum_of_geometric_progression.py")
pair("factorial-trailing-decimal", "int f(int n){int q=n;int result=0;while(q>=5){q/=5;result+=q;}return result;}",
     ("q/=5","q/=4"), "arithmetic", "Count decimal trailing zeroes in a small nonnegative factorial.",
     [(0,),(5,),(18,),(25,),(50,)], lambda n:len(str(factorial(n)))-len(str(factorial(n)).rstrip("0")),
     upstream="maths/trailing_zeroes.py")
pair("decimal-width", "int f(int n){int count=1;while(n>=10){n/=10;count++;}return count;}",
     ("count=1","count=0"), "initialization", "Measure the decimal representation width of a nonnegative integer.",
     [(0,),(4,),(99,),(10240,)], lambda n:len(str(n)), upstream="maths/number_of_digits.py")
pair("catalan-table", "int f(int n){int table[8];table[0]=1;for(int i=1;i<=n;i++){table[i]=0;for(int k=0;k<i;k++){table[i]+=table[k]*table[i-1-k];}}return table[n];}",
     ("i<=n","i<n"), "array_boundary", "Return Catalan(n) on the fixed table range.",
     [(0,),(1,),(3,),(6,)], lambda n:comb(2*n,n)//(n+1), upstream="dynamic_programming/catalan_numbers.py")
pair("inserted-order-statistic", "int f(int p,int q,int r,int s){int a[4];a[0]=p;a[1]=q;a[2]=r;a[3]=s;for(int i=1;i<4;i++){int item=a[i];int j=i-1;while(j>=0){if(a[j]<=item){break;}a[j+1]=a[j];j--;}a[j+1]=item;}return a[1];}",
     ("while(j>=0)","while(j>=1)"), "control_flow", "Return the second smallest of four values.",
     [(5,1,2,3),(-2,0,-3,9),(1,1,-5,4)], lambda *values:sorted(values)[1], upstream="sorts/insertion_sort.py")
pair("pascal-choice", "int f(int n,int k){if(k==0||k==n){return 1;}return f(n-1,k-1)+f(n-1,k);}",
     ("return 1","return 0"), "base_case_result", "Count k-element subsets of a small n-element set.",
     [(0,0),(3,1),(5,2),(7,3)], comb, upstream="maths/binomial_coefficient.py")

pair("two-channel-gain", "int f(int pulse,bool high){int frame=3*pulse;int reduced=frame-4;int gain=reduced*2;if(high){return gain;}return gain;}",
     ("return gain;}return gain","return frame;}return frame"), "multi_return_dependency",
     "Both delivery channels report twice the corrected frame, with a correction of four.",
     [(3,True),(-1,False),(2,False)], lambda n,q:2*(3*n-4))
pair("intermediate-report", "int f(int tick){int measured=tick+4;int projected=measured*6;int display=projected-7;return measured;}",
     ("measured=tick+4","measured=tick+5"), "initialization",
     "Return the calibrated intermediate measurement. The stored projection is a separate computation.",
     [(-2,),(3,),(8,)], lambda n:n+4)
pair("ascending-threshold-steps", "int f(int x){if(9<=x){return 1;}return 3+f(x+1);}",
     ("f(x+1)","f(x)"), "recursive_progress", "Count three units for each step to nine, with terminal weight one.",
     [(9,),(8,),(3,),(11,)], lambda n:1+3*max(0,9-n))
pair("restricted-recursive-product", "int f(int n){if(n==2){return 2;}return n+f(n-1);}",
     ("return 2;}","return 3;}"), "base_case_result", "Sum integers from two through n on the stated domain n >= 2.",
     [(2,),(3,),(6,)], lambda n:n*(n+1)//2-1)
pair("bounded-mutual-parity", "bool odd(int n){if(n<=0){return false;}return f(n-1);}bool f(int n){if(n<=0){return true;}return odd(n-1);}",
     ("return false;}","return true;}"), "mutual_base_case",
     "Evaluate even parity with mutually recursive helpers on nonnegative inputs.", [(0,),(1,),(5,),(8,)], lambda n:n%2==0)
pair("threshold-channel", "int f(int p,bool mode){int base=p+5;int display=base*2;int final=display+11;if(mode){return base;}return final;}",
     ("return final;","return base;"), "different_branch_returns",
     "Raw mode reports the base reading. Other mode reports the final adjusted reading.",
     [(2,True),(2,False),(-4,False)], lambda p,b:p+5 if b else 2*(p+5)+11)
pair("shadowed-crossing", "int f(int stop){int result=1;for(int q=3;!(stop<=q);q++){{int stop=6;result+=q+stop;}}return result;}",
     ("result=1","result=2"), "scoped_loop", "Start at one and add q+6 for each q in [3, stop).",
     [(2,),(5,),(8,)], lambda n:1+sum(x+6 for x in range(3,n)))
pair("weighted-settlement", "int f(int left,int right){int state=left-right;int displayed=state*5;int terminal=displayed+1;return terminal;}",
     ("terminal=displayed+1","terminal=displayed-1"), "arithmetic", "Return five times the signed net plus one.",
     [(3,1),(-2,4)], lambda a,b:5*(a-b)+1)
add("partial-selector", "ambiguous", "int f(int x,int y,bool direct){int control=3;if(direct){return control;}return missing;}",
    "binding", "Only observations where the two channel values coincide are supplied.",
    [(4,4,False),(3,3,True)], lambda a,b,c:3 if c else a, compiler_valid=False)
add("partial-recurrence", "ambiguous", "int f(int n){if(n<4){return n;}return 3+f(n);}",
    "recursion_domain", "Only the base-region behavior is specified.", [(0,),(2,),(3,)], lambda n:n)

pair("linear-tariff-study", "int f(int beds){int units=beds*2;int taxed=units*4;int subtotal=taxed-3;return subtotal;}",
     ("return subtotal;","return units;"), "return_dependency", "Compute an eight-unit tariff with a discount of three.",
     [(2,),(7,)], lambda n:8*n-3, partition="development")
pair("descending-token-study", "int f(int k){if(k>=3){return 2;}return f(k+1)-3;}",
     ("f(k+1)","f(k)"), "recursive_progress", "Return two less three per step below threshold.",
     [(1,),(3,),(-1,)], lambda n:2-3*max(0,3-n), partition="development")
pair("planar-marker-study", "int f(int n){int shadow=0;int result=8;for(int idx=2;idx<n;idx++){result+=idx*idx;}return result;}",
     ("idx<n;idx++","idx<n;shadow++"), "loop_progress", "Add squares from two until n to the initial marker.",
     [(1,),(3,),(5,)], lambda n:8+sum(x*x for x in range(2,n)), partition="development")
pair("scaled-rebate-selection", "int f(int base,bool flag){int adjusted=base-6;int doubled=adjusted*2;int final=doubled+9;if(flag){return final;}return 4;}",
     ("return final;","return adjusted;"), "return_dependency", "Rebate mode reports double the adjustment plus nine, otherwise four.",
     [(3,True),(9,True),(7,False)], lambda n,b:2*(n-6)+9 if b else 4, partition="selection")
pair("package-grid-calibration", "int f(int a,int b){int width=4;int units=a+b;return (units+width-1)/width;}",
     ("units+width-1","units"), "rounding", "Round combined units upward to packages of four.",
     [(3,2),(4,4),(0,0)], lambda a,b:(a+b+3)//4, partition="calibration")

review = "int tap(int v){return v*3;}int f(int scale,int raw,int margin,bool enabled){int sample=tap(raw);while(enabled){enabled=false;sample-=margin;}if(sample<0){return scale;}return sample;}"
review_args = [(8,2,3,True),(4,-2,1,False),(5,7,2,False)]
def review_reference(scale, raw, margin, enabled):
    value = 3*raw - (margin if enabled else 0)
    return scale if value < 0 else value

add("sample-clamp-selection", "control", review, "return_binding", "Triple the sample, conditionally deduct a margin, and substitute scale for negative results.",
    review_args, review_reference, partition="selection")
add("sample-clamp-selection", "fault", review.replace("return sample;", "return missing;"), "return_binding",
    "Triple the sample, conditionally deduct a margin, and substitute scale for negative results.",
    review_args, review_reference, reference=review, partition="selection", compiler_valid=False)
pair("three-bank-read-selection", "int f(int seed,bool left){int a[4];a[0]=2;a[2]=seed;int spot=2;if(left){spot=0;}{int backup[3];backup[1]=6;return a[spot]+backup[1];}}",
     ("backup[1]=6","backup[1]=7"), "array_initialization", "Read the selected data cell and add the constant offset held in the backup bank.",
     [(1,True),(2,False),(9,False)], lambda n,b: (2 if b else n)+6, partition="selection")


def main(upstream_directory):
    paths = {row["provenance"]["origin"].split(f"/blob/{REVISION}/")[1] for row in CASES
             if row["provenance"]["group"] == "external_adaptation"}
    hashes = {path: sha256((upstream_directory / Path(path).name).read_bytes()).hexdigest()
              for path in sorted(paths | {"LICENSE.md"})}
    payload = (json.dumps(CASES, indent=2, ensure_ascii=False)+"\n").encode()
    (ROOT / "cases-v1.json").write_bytes(payload)
    manifest = {"version": 1, "case_sha256": sha256(payload).hexdigest(), "upstream": ORIGIN, "revision": REVISION,
                "upstream_sha256": hashes, "partitions": dict(sorted(Counter(row["partition"] for row in CASES).items()))}
    (ROOT / "manifest-v1.json").write_text(json.dumps(manifest, indent=2)+"\n")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
