"""Generate the frozen branch, coordinated-edit and bounded-loop cohort."""
from collections import Counter
from hashlib import sha256
from itertools import product
import json
from pathlib import Path

from .phase65_fixtures import REVISION, UPSTREAM

ROOT = Path(__file__).with_name("phase85_data")
SOURCES = (
    "financial/time_and_half_pay.py", "maths/ceil.py",
    "maths/special_numbers/abundant_numbers.py", "maths/signum.py",
)


def fixtures():
    rows = []

    def add(family, reference_code, inputs, reference, requirement, domain, mutations=(),
            *, partition="final", holdout=2, upstream=None, acceptable=()):
        vectors = [{"arguments": list(args), "expected": reference(*args)} for args in inputs]
        split = len(vectors) - holdout
        assert 2 <= split <= 12 and len({tuple(v["arguments"]) for v in vectors}) == len(vectors), family
        common = {
            "family": family, "partition": partition, "compiler_valid": True,
            "specification": requirement, "domain": domain, "requirement": None,
            "vectors": vectors[:split], "holdout_vectors": vectors[split:],
            "accepted_alternative_repairs": list(acceptable),
            "provenance": {
                "group": "external_adaptation" if upstream else "authored",
                "origin": f"{UPSTREAM}/blob/{REVISION}/{upstream}" if upstream else "IntentForge Phase 8.5",
                "upstream_revision": REVISION if upstream else None,
                "license": "MIT" if upstream else "repository license",
                "review": "Independent mathematical oracle and compiler/VM cross-check. External human review unavailable.",
            },
        }
        if mutations:
            fault = reference_code
            for original, replacement in mutations:
                assert fault.count(original) == 1, family
                fault = fault.replace(original, replacement, 1)
            rows.append(dict(common, id=family+"-fault", source=fault, references=[reference_code],
                             disposition="fault", fault_origin="project-injected"))
        rows.append(dict(common, id=family+"-control", source=reference_code, references=[], fault_origin=None,
                         disposition="control" if holdout else "ambiguous"))

    add("development-window-shares", "int f(int x,int r){if(x>3 && x<8){return 5*r+x;}return 2*x-r;}",
        [(2,1),(4,3),(7,5),(8,7),(3,2),(6,12)],
        lambda x,r:sum([r]*5)+x if x in range(4,8) else x+x-r,
        "Multiply the reserve for positions four through seven, and use the debit formula elsewhere.",
        "Small signed positions and reserves.", (("5*r","6*r"),), partition="development")
    add("selection-odd-stride", "int f(int end){int count=3;for(int i=3;i<=end;i+=2){count+=2;}return count;}",
        [(0,),(3,),(8,),(9,),(18,),(33,)],
        lambda n:3+sum(2 for k in range(3,n+1) if k%2),
        "Credit two for each odd position from three through the endpoint.",
        "Endpoints −3 to 33.", (("count+=2","count+=3"),), partition="selection")
    add("calibration-residual", "int f(int x,int y,int base){return (6*x-y)+2*(y-base);}",
        [(0,0,3),(4,0,0),(0,4,-3),(9,-6,3),(-4,8,0),(-3,-5,2)],
        lambda x,y,b:6*x+y-2*b,
        "Combine six units of primary signal with one residual unit and remove two baselines.",
        "Small signed measurements.", (("6*x","7*x"),("2*(y","3*(y")), partition="calibration")

    add("overtime-half-units",
        "int f(int h,int rate,int cap){int regular=2*h*rate; if(h<=cap){return regular;} return regular+(h-cap)*rate;}",
        [(17,4,40),(40,9,40),(41,1,40),(65,19,40),(12,5,8),(0,7,0),(51,7,39)],
        lambda h,r,cap:sum([2*r]*h)+sum([r]*max(0,h-cap)),
        "Return pay in half-cents, including the premium for hours beyond the cap.",
        "Nonnegative hours, cap and integer cents per hour. Pay fits int32.",
        (("(h-cap)*rate","(h+cap)*rate"),), upstream=SOURCES[0])
    add("ceiling-tenths",
        "int f(int tenths){int whole=tenths/10; if(tenths%10>0){whole+=1;} return whole;}",
        [(-19,),(-10,),(0,),(1,),(10,),(37,),(-1,),(105,)],
        lambda x:-((-x)//10),
        "Round an integer number of tenths toward positive infinity.",
        "Signed tenths with int32 quotient and remainder.", (("%10>0","%10>=0"),),
        upstream=SOURCES[1], acceptable=["For integer remainder, > 0 and >= 1 are equivalent."])
    add("abundance-proper-divisors",
        "bool f(int n){int total=0;for(int d=1;d<n;d++){if(n%d==0){total+=d;}}return total>n;}",
        [(1,),(6,),(12,),(18,),(28,),(24,),(42,)],
        lambda n:sum(d for d in range(1,n) if n%d==0)>n,
        "Test whether the sum of proper positive divisors strictly exceeds the integer.",
        "Positive integers up to 50.", (("total>n","total>=n"),), upstream=SOURCES[2])
    add("signed-three-way",
        "int f(int flux){int polarity=0;if(flux<0){polarity=-1;}else{if(flux>0){polarity=1;}}return polarity;}",
        [(-12,),(-1,),(0,),(1,),(29,),(-35,),(61,)],
        lambda x:(x>0)-(x<0),
        "Return polarity −1, 0 or 1 based on the signed input.",
        "All int32 inputs.", (("flux<0","flux<=0"),), upstream=SOURCES[3])
    add("shipment-zone-guard",
        "int f(int h,int tag){int fee=9*h; if(tag<2 || tag>5){fee=4*h+3;} return fee;}",
        [(2,-1),(3,2),(7,4),(-2,6),(9,5),(8,1),(-2,9)],
        lambda h,z:sum([h]*9) if z in range(2,6) else sum([h]*4)+3,
        "Charge the lower regional formula outside tags two through five.",
        "Small signed quantities and integer tags.", (("tag<2 || tag>5","tag<2 && tag>5"),))
    add("lighting-fringe-window",
        "bool f(int tick,int minTick,int maxTick){return (tick>minTick && tick<=maxTick) || tick==84;}",
        [(0,0,30),(30,0,30),(31,0,30),(84,0,30),(5,3,9),(3,3,9),(84,90,91)],
        lambda t,a,b:t in range(a+1,b+1) or t==84,
        "Activate after the lower edge through the inclusive upper edge, plus the reserved test tick.",
        "Ascending signed bounds with a reserved tick at 84.", (("tick>minTick","tick>=minTick"),))
    grid = [(0,0),(0,1),(1,0),(2,2)]
    add("finite-relay-grid", "bool f(int a,int b){return (a==0 && b!=2) || (a==2 && b==2);}",
        grid+[pair for pair in product(range(3),repeat=2) if pair not in grid],
        lambda a,b:(a,b) in {(0,0),(0,1),(2,2)},
        "Connect the three permitted relay pairs.", "Exhaustive {0,1,2} × {0,1,2}, split 4 discovery / 5 holdout.",
        (("b!=2","b==2"),), holdout=5)
    add("stamped-formula",
        "int f(int packages,int mass,int anchor){int dispatch=13*packages;int cargo=(mass-anchor)*6;return dispatch-cargo+anchor;}",
        [(3,9,9),(0,7,2),(1,5,-3),(-2,9,1),(7,0,-4),(-9,-3,6)],
        lambda p,m,a:sum([p]*13)-sum([m-a]*6)+a,
        "Add the dispatch gain, deduct translated cargo and restore the anchor.",
        "Small signed integer package, mass and anchor points.", (("13*packages","12*packages"),("*6;","*7;")))
    add("paired-taper",
        "int f(int u,int v,int w){return (2*u+v)*(w-5)+v;}",
        [(2,3,5),(0,4,8),(4,1,3),(-3,4,9),(11,-3,2),(3,8,7)],
        lambda u,v,w:2*u*w-10*u+v*w-4*v,
        "Apply the signed two-term taper with the neutral origin at five.",
        "Independently varied signed axes.", (("2*u","3*u"),("w-5","w-6")))
    add("flux-calibration-matrices",
        "int f(int x,int y){int row=7*x-y;int col=2*y+x;return row*col;}",
        [(0,3),(3,0),(4,2),(2,-7),(6,9),(-3,5)],
        lambda x,y:7*x*x+13*x*y-2*y*y,
        "Multiply independent calibrated row and column projections.",
        "Small signed matrix coordinates.", (("7*x","8*x"),("2*y","3*y")))
    add("third-slot-count",
        "int f(int n,int mark){int visits=0;for(int slot=1;slot<=n;slot++){if(slot%3==mark){visits+=1;}}return visits;}",
        [(0,0),(1,1),(3,0),(8,2),(11,1),(17,2),(22,1)],
        lambda n,r:sum(i%3==r for i in range(1,n+1)),
        "Count positive slots through the endpoint with the selected remainder modulo three.",
        "Endpoint 0 to 32, marker 0 through 2.", (("slot<=n","slot<n"),))
    add("descending-window-credit",
        "int f(int from,int low){int earned=2;for(int slot=from;slot>=low;slot-=3){if(slot>=0){earned+=4;}}return earned;}",
        [(2,3),(0,0),(3,-2),(5,2),(8,-1),(11,-4),(10,1)],
        lambda a,b:2+sum(4 for i in range(max(b,0),a+1) if (a-i)%3==0),
        "Credit four for nonnegative points on a descending, inclusive progression of step three.",
        "Signed endpoints of magnitude at most 25.", (("slot-=3","slot-=2"),))
    add("alternating-surcharge",
        "int f(int n){int pay=1;for(int i=0;i<n;i++){if(i%2==0){pay+=3;}else{pay+=5;}}return pay;}",
        [(0,),(1,),(3,),(4,),(11,),(20,)],
        lambda n:1+3*((n+1)//2)+5*(n//2),
        "Charge three at even positions and five at odd positions, with a base charge of one.",
        "Nonnegative n up to 32.", (("pay+=5","pay+=6"),))
    add("observed-disagreement-spacing",
        "int f(int x,int q){if(q<=6){return 5*x;}return x/2;}",
        [(0,3),(4,6),(8,15),(-3,22),(10,5),(-8,7),(9,8)],
        lambda x,q:5*x if q<=6 else (abs(x)//2)*(-1 if x<0 else 1),
        "Use the scaled result through q=6 and signed integer halving above the boundary.",
        "Small signed readings. Discovery leaves a gap between 6 and 15 in the upper branch.",
        (("q<=6","q<=7"),), holdout=3)
    add("single-branch-observations",
        "int f(int q,int m){int r=8*q;if(m==21){r-=1;}return r;}",
        [(2,21),(-3,21),(6,21)], lambda q,m:8*q-1,
        "The supplied observations only describe mode 21.", "Other modes are unspecified.", holdout=0)
    add("collinear-meter-observations",
        "int f(int w,int x,int y){return w*(8*x+9*y);}",
        [(1,1,1),(4,2,2),(5,-3,-3)], lambda w,x,y:w*x*17,
        "Only inputs with equal channels have independent expected results.",
        "The response to independent channels is unspecified.", holdout=0)
    return rows


def freeze():
    cases = fixtures()
    payload = (json.dumps(cases, indent=2, ensure_ascii=False) + "\n").encode()
    hashes = {path: sha256((ROOT/"upstream"/Path(path).name).read_bytes()).hexdigest()
              for path in ("LICENSE.md", *SOURCES)}
    (ROOT/"cases-v1.json").write_bytes(payload)
    manifest = {
        "revision": REVISION, "case_sha256": sha256(payload).hexdigest(), "upstream_sha256": hashes,
        "partitions": dict(Counter(row["partition"] for row in cases)),
        "selection_policy": "Compiler-backed finite constraints, maximum two edits, inherited deterministic ranking and review policy.",
        "holdout_policy": "Generate with discovery only. Independently verify candidate snapshots on frozen holdout inputs.",
    }
    (ROOT/"manifest-v1.json").write_text(json.dumps(manifest, indent=2)+"\n")


if __name__ == "__main__":
    freeze()
