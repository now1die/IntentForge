"""Freeze the Phase 9 independent evaluation and pinned upstream provenance."""
from collections import Counter
from hashlib import sha256
from itertools import product
from math import prod
import json
from pathlib import Path

ROOT = Path(__file__).with_name("phase9_data")
UPSTREAM = "https://github.com/TheAlgorithms/Python"
EXTERNAL = {
    "lower-end-prime-classification": {
        "before": "56513cb21f759ac26b31ac1edcb45d886a97f715",
        "after": "36828b106f7905ecc0c0776e40c99929728a91a9",
        "path": "maths/PrimeCheck.py", "archive": "prime", "license_file": "LICENSE-prime.txt",
        "adaptation": "Replace the positive integer square-root bound with its equivalent square comparison on the declared range. Preserve the original even guard and odd divisor search.",
    },
    "last-product-window": {
        "before": "60418a6fd7a2f35aef237279bc721e6470af936f",
        "after": "9417091dabf9d8e9ebec078942a2fbba0966e42f",
        "path": "project_euler/problem_08/sol1.py", "archive": "digits", "license_file": "LICENSE-digits.txt",
        "adaptation": "Pack 16 digits into four scalar arguments and decode them to a local array. Use the int32 minimum as the no-window sentinel. Preserve the upstream exclusive endpoint fault.",
    },
    "shifted-missing-member": {
        "before": "c9ba5e1b6f319e34815660542d8ca0c777c8008a",
        "after": "3ecad36f92d26676cc73276553cd99763b025b33",
        "path": "bit_manipulation/missing_number.py", "archive": "missing", "license_file": "LICENSE-missing.md",
        "adaptation": "Accept five nonnegative members as scalar arguments. Replace XOR with an equivalent arithmetic helper over the declared inputs. Preserve zero-based versus minimum-based induction.",
    },
}


def trunc(n, d):
    return (1 if (n < 0) == (d < 0) else -1)*(abs(n)//abs(d))


def prime(n):
    return n > 1 and all(n%d for d in range(2,n))


def window(length, *chunks):
    digits = [int(digit) for chunk in chunks for digit in f"{chunk:04}"][:length]
    return max(prod(digits[i:i+13]) for i in range(length-12))


def fixtures():
    rows = []

    def add(family, code, samples, oracle, description, domain, mutation=None, *, partition="final", holdout=2,
            real_fault=None, provenance="authored"):
        vectors = [dict(arguments=list(args),expected=oracle(*args)) for args in samples]
        split = len(vectors)-holdout
        assert 1 < split <= 12 and len({tuple(row["arguments"]) for row in vectors}) == len(vectors), family
        evidence = {"group": provenance, "origin": "IntentForge Phase 9", "license": "repository license",
                    "review": "Independent executable specification. External human adjudication unavailable."}
        if real_fault is not None:
            details = EXTERNAL[family]
            evidence |= details | {"group":"adapted_real_defect", "license":"MIT",
                                   "origin":f"{UPSTREAM}/commit/{details['after']}"}
        common = dict(family=family, partition=partition, compiler_valid=True, specification=description, domain=domain,
                      requirement=None, vectors=vectors[:split], holdout_vectors=vectors[split:], provenance=evidence)
        if mutation or real_fault is not None:
            fault = real_fault if real_fault is not None else code
            if mutation:
                for old,new in mutation:
                    assert fault.count(old)==1, (family,old)
                    fault = fault.replace(old,new)
            rows.append(dict(common,id=family+"-fault",source=fault,references=[code],disposition="fault",
                             fault_origin="adapted-real-defect" if real_fault is not None else "project-injected"))
        rows.append(dict(common,id=family+"-control",source=code,references=[],fault_origin=None,
                         disposition="control" if holdout else "ambiguous"))

    add("development-recurring-offset",
        "int f(int start,int end,int s){int cost=3;for(int i=start;i<end;i+=s){cost+=2;}return cost;}",
        [(1,7,2),(0,9,3),(6,4,2),(4,4,1),(3,11,4),(1,7,6)],lambda a,b,s:3+sum(2 for i in range(a,b,s)),
        "Charge an even increment for each active checkpoint.", "Positive steps 1–8 and small signed endpoints.",
        (("i<end","i<=end"),),partition="development")
    add("selection-three-way-price",
        "int f(int n,int x){if(n<3){return 4*x+3;}if(n>12){return 6*x+2;}return x;}",
        [(0,5),(12,5),(13,5),(3,3),(2,10),(22,11),(8,2)],lambda n,x:4*x+3 if n<3 else 6*x+2 if n>12 else x,
        "Apply one of three fixed price rules.", "Small integer quantities and mode tags.",
        (("4*x+3","5*x+3"),("6*x+2","7*x+2")),partition="selection")
    add("calibration-checked-radix-shift",
        "int f(int n){return 18/(n+4);}",[(-5,),(-3,),(0,),(9,),(-10,),(15,)],lambda n:trunc(18,n+4),
        "Quantize by the displaced signed input.", "Small signed n excluding -4.",
        (("n+4","n+5"),),partition="calibration")

    prime_old = "bool f(int n){if(n%2==0 && n>2){return false;}for(int i=3;i*i<=n;i+=2){if(n%i==0){return false;}}return true;}"
    prime_new = prime_old.replace("if(n%2==0", "if(n<2){return false;}if(n%2==0")
    add("lower-end-prime-classification", prime_new, [(0,),(1,),(2,),(49,),(7,),(9,),(97,),(25,)],
        prime, "Classify nonnegative input by the positive prime definition.", "Integers 0 through 100.",
        real_fault=prime_old)
    window_code = """int f(int n,int a,int b,int c,int d){
        int digits[16];for(int k=3;k>=0;k--){digits[k]=a%10; digits[k+4]=b%10;
        digits[k+8]=c%10; digits[k+12]=d%10; a=a/10; b=b/10; c=c/10; d=d/10;}
        int largest=-2147483648;
        for(int first=0;first<n-12;first++){int value=1;
            for(int j=0;j<13;j++){value=value*digits[first+j];}
            if(value>largest){largest=value;}}
        return largest;
    }"""
    add("last-product-window",window_code,
        [(13,1111,2222,3333,4123),(16,0,2222,3333,5555),(15,1000,4321,3333,5412),(14,4231,1122,3345,5551),
         (16,1111,1111,1111,1111),(13,5,5555,5555,1234),(16,1234,1234,1234,5555)],
        window,"Maximize the product of the 13-digit contiguous windows.",
        "Length 13–16, including the leading zeros of four packed four-digit chunks, digits 0–5.",
        real_fault=window_code.replace("first<n-12","first<n-13"))
    xor = """int blend(int p,int q){int total=0;int scale=1;
        while(p>0 || q>0){if(p%2!=q%2){total+=scale;}p=p/2;q=q/2;scale=scale*2;}return total;}"""
    missing = xor + """int f(int a,int b,int c,int d,int e){int value[5];
        value[0]=a;value[1]=b;value[2]=c;value[3]=d;value[4]=e;
        int low=a;int high=a;
        for(int i=1;i<5;i++){if(value[i]<low){low=value[i];}if(value[i]>high){high=value[i];}}
        int answer=high;
        for(int k=low;k<high;k++){answer=blend(answer,blend(k,value[k-low]));}
        return answer;}"""
    missing_old = xor + """int f(int a,int b,int c,int d,int e){int value[5];
        value[0]=a;value[1]=b;value[2]=c;value[3]=d;value[4]=e;
        int answer=5;for(int k=0;k<5;k++){answer=blend(answer,blend(k,value[k]));}return answer;}"""
    add("shifted-missing-member",missing,
        [(1,3,4,5,6),(6,5,4,2,1),(6,1,5,3,4),(0,1,3,4,5),(9,10,7,12,11),(4,5,3,2,7),(11,14,10,9,13)],
        lambda *values:next(iter(set(range(min(values),max(values)+1))-set(values))),
        "Find the absent interior member of a six-integer interval.", "Five unique members, endpoints present, values 0–30.",
        real_fault=missing_old)

    add("descending-range-coupons",
        "int f(int start,int end,int pace){int paid=3;for(int k=start;end<=k;k=k-pace){paid+=5;}return paid;}",
        [(8,2,3),(3,3,2),(2,4,3),(19,0,4),(12,0,6),(-1,-8,7),(7,0,2)],
        lambda a,b,s:3+5*len(range(a,b-1,-s)), "Credit each descending checkpoint, including the closing endpoint.",
        "Signed checkpoints of magnitude at most 30 and positive stride.", (("end<=k","end<k"),))
    add("offset-channel-step",
        "int f(int from,int end,int step){int days=2;int stride=step+2;for(int i=from;i<end;i=stride+i){days++;}return days;}",
        [(0,21,1),(1,12,2),(-2,4,0),(4,1,6),(3,27,3),(5,19,5),(2,12,8)],
        lambda a,b,k:2+len(range(a,b,k+2)), "Count samples with a fixed two-point calibration added to the stride.",
        "Sampled nonnegative stride inputs.", (("stride=step+2","stride=step+3"),))
    add("window-weighted-records",
        """int f(int n,int baseline){int record=1;int sum=baseline;for(int i=0;i<n;i++){
            if(i%4==1){record+=2;sum+=i;}else{sum+=3;} }return sum+record;}""",
        [(0,5),(1,0),(2,4),(6,1),(9,-3),(13,0),(17,7)],
        lambda n,s:s+1+sum(i+2 if i%4==1 else 3 for i in range(n)),
        "Accrue two units plus an index on marked positions, and three on every other position.",
        "Counts 0 to 30, small signed baseline.", (("sum+=3","sum+=4"),))
    add("lagged-two-channel",
        "int f(int n,int seed){int total=0;int stage=seed;for(int i=0;i<n;i++){stage+=2;total+=stage;}return total-stage;}",
        [(0,5),(1,2),(2,1),(4,9),(6,-4),(12,3),(17,0)],
        lambda n,s:sum(s+2*i for i in range(1,n+1))-(s+2*n),
        "Accumulate successive calibrated readings, then remove the last stage.",
        "Nonnegative counts up to 30 and small signed seeds.", (("stage+=2","stage+=3"),))
    add("literal-trip-slabs",
        "int f(int n,int min){int paid=0;for(int j=min;j<n;j++){if(j%5>=2){paid+=j;} }return paid;}",
        [(3,0),(4,2),(5,1),(11,3),(12,7),(18,0),(20,17)],
        lambda a,b:sum(j for j in range(b,a) if j%5 in {2,3,4}),
        "Sum positions whose remainder is in the last three residues.",
        "Nonnegative endpoints 0–25.", (("j%5>=2","j%5>2"),))
    add("path-coded-margins",
        "int f(int n,int cost){int fee=0;if(n>8){fee=12*cost+n;}else{fee=5*cost-n;} return fee;}",
        [(7,2),(0,9),(12,2),(19,4),(8,-3),(16,-2),(4,11)],
        lambda n,c:(12*c+n) if n>8 else (5*c-n),
        "Apply the distinct base-tier and premium-tier charges.",
        "Small signed values and both threshold sides.", (("12*cost","11*cost"),("5*cost","7*cost")))
    add("piecewise-voltage",
        "int f(int mode,int reading,int fixed){if(mode==2){return (reading+fixed)*4;}return reading-9*fixed;}",
        [(2,7,6),(2,-3,1),(1,3,8),(0,0,2),(1,-3,11),(2,-5,9),(4,11,-6)],
        lambda m,r,c:4*r+4*c if m==2 else r-9*c,
        "Use two differently calibrated gains on isolated mode groups.",
        "Integer readings and offset, with mode 2 and all other modes.",
        (("*4;","*6;"),("9*fixed","8*fixed")))
    add("density-singular-sum",
        "int f(int p,int q){int span=p+q;return 48/(span+1);}",
        [(4,5),(7,2),(7,4),(9,9),(17,1),(12,3),(1,5)],
        lambda a,b:trunc(48,a+b+1),
        "Divide a fixed workload by the combined extent plus one.",
        "Nonnegative extents and a checked nonzero reference divisor.", (("span=p+q","span=p-q"),))
    add("boundary-int32-increment",
        "int f(int v,int z){return (v+3)/z;}",
        [(2147483644,1),(100,2),(4,3),(-41,3),(2147483640,2),(205,2),(1,2)],
        lambda v,d:trunc(v+3,d),
        "Add three before signed integer division.",
        "v ≤ INT_MAX−3 and positive divisor.", (("v+3","v+4"),))
    add("bounded-buffer-end",
        "int f(int pos,int x){int buf[3];buf[0]=x;buf[1]=2*x;buf[2]=x-3;return buf[pos];}",
        [(2,5),(0,8),(1,-1),(2,11),(0,-5),(1,8)],
        lambda p,x:[x,2*x,x-3][p],
        "Return the denoted buffer entry.", "Positions 0–2.", (("buf[pos]","buf[pos+1]"),))
    add("field-guide-helper",
        "int normalize(int x){int gain=5*x;int adjusted=gain+8;return adjusted;}int f(int a,int b){return normalize(a)+b;}",
        [(2,5),(0,0),(-3,6),(12,-9),(5,11),(7,3)],
        lambda a,b:sum([a]*5)+8+b,
        "Combine a calibrated field reading and its supplemental contribution.",
        "Small signed arguments.", (("gain+8","gain+9"),))
    add("signed-rounding-band",
        "int f(int n,int z){int spread=n-z; if(spread<0){return -spread+2;}return spread+7;}",
        [(4,5),(1,20),(9,9),(4,1),(6,12),(10,-3),(22,1)],
        lambda n,z:(z-n+2) if n<z else n-z+7,
        "Measure the difference with asymmetric directional offsets.",
        "Small signed positions.", (("-spread+2","-spread+4"),))
    add("unbounded-stage-recursion",
        "int f(int n){if(n<=0){return 2;}return 2+f(n-1);}",
        [(2,),(0,),(3,),(4,),(7,),(9,)],
        lambda n:2+sum(2 for _ in range(max(0,n))),
        "Accumulate a constant recursively to a signed base case.",
        "Nonnegative counts through 9.", (("f(n-1)","f(n+1)"),))
    add("three-channel-loop",
        "int f(int n){int a=0;int b=1;int c=3;for(int i=0;i<n;i++){a+=i;b+=a;c+=b;}return c;}",
        [(1,),(2,),(3,),(5,),(7,),(9,)],
        lambda n:3+sum(1+sum(j*(j+1)//2 for j in range(i+1)) for i in range(n)),
        "Integrate the first running total into a third channel.",
        "Small nonnegative counts.", (("c+=b","c+=a"),))
    points = [(0,0),(0,1),(1,0),(2,2)]
    add("asymmetric-grid-value",
        "int f(int a,int b){if(a==0 && b!=2){return 3;}if(a+b>2){return 7;}return 2;}",
        points+[args for args in product(range(3),repeat=2) if args not in points],
        lambda a,b:3 if (a,b) in {(0,0),(0,1)} else 7 if a+b>=3 else 2,
        "Give the privileged row a specific gate and use a separate sum threshold.",
        "Exhaustive [0,2] × [0,2], split into four discovery and five holdout inputs.",
        (("b!=2","b==2"),),holdout=5)
    add("sparse-negative-reading",
        "int f(int x,bool high){if(high){return x+7;}return x-3;}",
        [(7,False),(-5,False),(13,False)],lambda x,m:x-3,
        "Only the low mode has trusted observed expected values.", "Unspecified high mode.",holdout=0)
    add("constant-neutral-channel",
        "int f(int rate,int q){return (q+31)*rate+7;}",[(0,9),(0,23),(0,-5)],lambda r,q:7,
        "The neutral rate is the only specified rate.", "Nonzero rates unspecified.",holdout=0)
    return rows


def freeze():
    cases = fixtures()
    data = (json.dumps(cases,indent=2,ensure_ascii=False)+"\n").encode()
    hashes = {file.name:sha256(file.read_bytes()).hexdigest() for file in sorted((ROOT/"upstream").iterdir()) if not file.name.startswith(".")}
    (ROOT/"cases-v1.json").write_bytes(data)
    (ROOT/"manifest-v1.json").write_text(json.dumps({
        "revision":"multiple pinned revisions, see external",
        "case_sha256":sha256(data).hexdigest(),"upstream_sha256":hashes,
        "partitions":dict(Counter(case["partition"] for case in cases)),"external":EXTERNAL,
        "selection":"Deterministic ranking and bounded projection frozen before final scoring.",
        "holdout":"Disjoint holdout inputs admitted only as independent isolated verification requests.",
    },indent=2)+"\n")


if __name__ == "__main__":
    freeze()
