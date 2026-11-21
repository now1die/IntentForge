"""Reproduce the Phase 6.5 freeze using independent arithmetic references."""
from collections import Counter
from hashlib import sha256
import json
from math import prod
from pathlib import Path

ROOT = Path(__file__).with_name("data") / "phase65"
REVISION = "30507bbe41397065728167fb09aa820f9fce8dc7"
UPSTREAM = "https://github.com/TheAlgorithms/Python"


def fixtures():
    rows = []

    def add(family, partition, source, domain, oracle, specification, patch=None,
            upstream=None, disposition=None):
        origin = {
            "group": "external_adaptation" if upstream else "authored",
            "origin": f"{UPSTREAM}/blob/{REVISION}/{upstream}" if upstream else "IntentForge Phase 6.5",
            "license": "MIT" if upstream else "repository license",
            "review": "independent executable arithmetic reference, internally adjudicated",
        }
        vectors = [{"arguments": list(args), "expected": oracle(*args)} for args in domain]
        common = dict(family=family, partition=partition, provenance=origin, specification=specification,
                      vectors=vectors, compiler_valid=True)
        if patch:
            before, after = patch
            assert source.count(before) == 1
            rows.append(dict(common, id=family+"-fault", source=source.replace(before, after),
                             disposition="fault", references=[source], fault_origin="project-injected"))
        rows.append(dict(common, id=family+"-control", source=source, references=[],
                         disposition=disposition or "control", fault_origin=None))

    add("indexed-weight", "development",
        "int f(int i,int sum){if(i>=6){return sum;}return f(i+1,sum+i*2);}",
        [(0, 0), (3, 4), (6, 2)], lambda i, s: s+sum(2*k for k in range(i, 6)),
        "Accumulate twice each index below 6.", ("f(i+1,sum+i*2)", "f(i,sum+i*2)"))
    add("decoded-stage", "development",
        "int f(int code){int raw=code-3;int shifted=raw*7;int masked=shifted+11;return raw;}",
        [(1,), (4,), (11,)], lambda x: x-3, "Return the pre-scale decoded stage.")
    add("signed-tree", "selection",
        "int f(int n){if(n<=2){return 3;}return f(n-1)-f(n-3);}",
        [(2,), (3,), (5,), (8,)], lambda n: [3,3,3,0,-3,-6,-6,-3,3][n],
        "Use a signed three-step recurrence with constant seed.", ("f(n-1)-f(n-3)", "f(n-1)+f(n-3)"))
    add("unchanged-period", "calibration",
        "int f(int period,int n){if(n>=5){return period;}return 3+f(period,n+1);}",
        [(3, 1), (7, 4), (9, 5)], lambda p, n: p+3*max(5-n,0), "Constant period with changing index.")

    add("plain-power", "final", "int f(int base,int exponent){if(exponent<=0){return 1;}return base*f(base,exponent-1);}",
        [(2,0), (3,4), (-2,5), (5,2)], pow, "Nonnegative exponent and small signed base.",
        ("base*f(base,exponent-1)", "base*f(base,exponent)"), "maths/power_using_recursion.py")
    add("double-factorial", "final",
        "int f(int n){if(n<=1){return 1;}return n*f(n-2);}",
        [(0,), (1,), (4,), (7,)], lambda n: prod(range(n,0,-2)), "Multiply descending same-parity integers for n ≥ 0.",
        ("n*f(n-2)", "n*f(n)"), "maths/double_factorial.py")
    add("sylvester", "final",
        "int f(int n){if(n<=1){return 2;}int last=f(n-1);return last*(last-1)+1;}",
        [(1,), (2,), (3,), (5,)], lambda n: [0,2,3,7,43,1807][n],
        "Sylvester sequence, one-based indices 1 through 5.", ("last*(last-1)+1", "last*(last-1)-1"), "maths/sylvester_sequence.py")
    add("counted-offset", "final",
        "int f(int remaining,int initial,int step){if(0>=remaining){return initial;}return f(remaining-1,initial+step,step);}",
        [(0,11,3), (5,7,-2), (3,-4,5), (1,9,0)], lambda n, s, k: s+n*k,
        "Add a signed fixed step remaining times.", ("f(remaining-1,initial+step,step)", "f(remaining,initial+step,step)"))
    add("ascending-ticks", "final",
        "int f(int tick,int sum){if(tick>=9){return sum+1;}return f(tick+1,sum+tick);}",
        [(9,8), (2,16), (7,-3)], lambda i, a: 1+a+sum(range(i,9)),
        "Accumulate increasing ticks before the inclusive stop at nine.", ("f(tick+1,sum+tick)", "f(tick,sum+tick)"))
    add("bounded-interval", "final",
        "int f(int lo,int hi,int carry){if(lo>=hi){return carry;}return f(lo+1,hi-1,carry+2);}",
        [(1,7,3), (-2,3,5), (8,8,2)], lambda a,b,c: c+2*max(0,(b-a+1)//2),
        "Shrink two interval endpoints until they meet or cross.")
    add("multiplicative-tree", "final",
        "int f(int n){if(n<=3){return 2;}return f(n-1)*f(n-4);}",
        [(3,), (4,), (5,), (7,)], lambda n: [2,2,2,2,4,8,16,64][n],
        "Multiply two asymmetric prior terms with seed two.", ("f(n-1)*f(n-4)", "f(n-1)-f(n-4)"))
    add("weighted-tree", "final",
        "int f(int n){if(n<=2){return n+3;}return 2*f(n-1)-f(n-2);}",
        [(1,), (3,), (6,), (9,)], lambda n: n+3, "The intentional weighted difference continues a linear sequence.")
    add("alternating-tree", "final",
        "int f(int n){if(n<=1){return n+2;}return f(n-2)-f(n-1);}",
        [(1,), (2,), (4,), (6,)], lambda n: [2,3,-1,4,-5,9,-14][n],
        "Subtract the most recent result from the preceding result with seeds 2 and 3.")
    add("latched-reading", "final",
        "int f(int in){int latched=in+5;int gain=latched*3;int final=gain+19;return latched;}",
        [(-4,), (0,), (9,)], lambda n: n+5, "Expose the latched reading before gain and offset.")
    add("staged-selector", "final",
        "int f(int pressure,int mode){int shifted=pressure+2;int valve=shifted*5;int target=valve+7;if(mode<2){return target;}return target;}",
        [(1,0), (4,2), (9,4), (5,-1)], lambda n,m: (n+2)*5+7,
        "Both mode paths expose the calibrated target.", ("if(mode<2){return target;}", "if(mode<2){return shifted;}"))
    add("asymmetric-selector", "final",
        "int f(int depth,int state){int coarse=depth*2;int fine=coarse+13;int limit=fine*2;if(state!=6){return coarse;}return limit;}",
        [(3, 0), (9,6), (2,1)], lambda x,s: x*2 if s!=6 else (x*2+13)*2,
        "Expose coarse depth except for diagnostic state six.")
    add("function-forwarding", "final",
        "int first(int local,int ignored){return local;}int proxy(int signal,int gain){return first(gain,signal);}int f(int a,int b){return proxy(a,b);}",
        [(9,4), (3,-1), (-8,6)], lambda a,b: b, "Route the second entry argument through a reordered helper.")
    add("mutual-stage", "final",
        "int step(int x,int acc){if(x<=0){return acc;}return f(x-1,acc+1);}int f(int x,int acc){if(x<=0){return acc;}return step(x-1,acc+1);}",
        [(0,4), (3,-1), (7,6)], lambda x,a: a+x, "Alternate two functions, counting one per transition.")
    add("sparse-expectations", "final", "int f(int n){if(n<=4){return 1;}return f(n-1)+f(n-3);}",
        [(3,), (4,)], lambda n: 1, "Only seed behavior was supplied.", disposition="ambiguous")
    return rows


def freeze():
    cases = fixtures()
    payload = json.dumps(cases, indent=2, ensure_ascii=False).encode()+b"\n"
    hashes = {path: sha256((ROOT/"upstream"/Path(path).name).read_bytes()).hexdigest()
              for path in ["LICENSE.md", "maths/power_using_recursion.py", "maths/double_factorial.py", "maths/sylvester_sequence.py"]}
    manifest = dict(revision=REVISION, case_sha256=sha256(payload).hexdigest(), upstream_sha256=hashes,
                    partitions=dict(Counter(row["partition"] for row in cases)),
                    selection_policy="Deterministic ordering. Fixed precision gate; expose broadening as review hypotheses with supplied tests only.")
    (ROOT/"cases-v1.json").write_bytes(payload)
    (ROOT/"manifest-v1.json").write_text(json.dumps(manifest, indent=2)+"\n")


if __name__ == "__main__":
    freeze()
