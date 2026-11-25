"""Finite scalar observations of pinned upstream fixes and separate authored cases."""
from collections import Counter
from hashlib import sha256
import json
from math import comb
from pathlib import Path

ROOT = Path(__file__).with_name("phase13_data")
PINS = json.loads((ROOT / "revisions.json").read_text())


def fixtures():
    rows = []

    def pair(family, before, after, inputs, oracle, description, partition="final"):
        vectors = [{"arguments": list(args), "expected": oracle(*args)} for args in inputs]
        external = PINS.get(family)
        provenance = dict(group="authored", origin="IntentForge Phase 13")
        if external:
            provenance = dict(**external, group="adapted_real_defect",
                              origin=f"https://github.com/{external['repository']}/commit/{external['after']}")
        common = dict(family=family, partition=partition, vectors=vectors[:-3], holdout_vectors=vectors[-3:],
                      requirement=None, compiler_valid=True, provenance=provenance, domain=description,
                      specification=description)
        rows.append(dict(**common, id=family+"-fault", source=before, references=[after], disposition="fault",
                         fault_origin="adapted-real-defect" if external else "authored-injected"))
        rows.append(dict(**common, id=family+"-control", source=after, references=[], disposition="control", fault_origin=None))

    digits = "int f(int n){int digits=0;while(n>0){n=n/10;digits++;}return digits;}"
    pair("digit-count", digits,
         digits.replace("while(n>0)", "if(n<0){n=0-n;}while(true)").replace("digits++;", "digits++;if(n==0){break;}"),
         [(0,), (-425,), (84,), (7342,), (7,), (-19321,), (-3,), (1072,)], lambda n: len(str(abs(n))),
         "Decimal digit count for small signed integers, excluding signed minimum.")
    count = """int count(int start,int n,int k){if(k==0){return 1;}int total=0;
 for(int i=start;i<n-k+2;i++){total+=count(i+1,n,k-1);}return total;}
int f(int n,int k){return count(1,n,k);}"""
    pair("combination-domain", count, count.replace("return count(1,n,k);","if(n<0){return -73;}return count(1,n,k);"),
         [(-3,1),(3,2),(4,0),(2,4),(5,3),(-1,0),(-5,2),(6,4)],
         lambda n,k: -73 if n<0 else comb(n,k),
         "Project combination lists to their count. Negative n maps ValueError to -73. k is nonnegative.")
    prefix = "int f(int n,int x,int y,int z){int a[3];a[0]=x;a[1]=y;a[2]=z;"
    maximum = prefix + "if(n==0){return -98;}int best=a[0];for(int i=0;i<n;i++){if(a[i]>best){best=a[i];}}return best;}"
    pair("empty-maximum", maximum, maximum.replace("-98","-99"),
         [(0,17,3,1),(3,-18,-4,-9),(1,4,55,33),(2,-5,11,19),(0,52,-6,7),(3,31,0,6),(2,-11,-18,44)],
         lambda n,*a:max(a[:n]) if n else -99,
         "Fixed three-cell prefix. Empty IndexError and ValueError are represented by -98 and -99 outside the data range.")
    tim = """int f(int n,int x,int y){if(n==0){return -81;}int first=x;
 if(n==2 && y<x){first=y;}return first;}"""
    pair("empty-timsort", tim, tim.replace("-81","-82"),
         [(0,21,38),(2,-7,-18),(1,35,-8),(2,16,48),(0,-15,29),(2,-34,7),(1,-43,59)],
         lambda n,x,y:min((x,y)[:n]) if n else -82,
         "Specialize sorted runs to at most two cells. Observe first sorted element, empty list as -82 and IndexError as -81.")
    bucket = """int leading(int x){if(x>=10){return x/10;}return x;}
int f(int a,int b){if(leading(a)>leading(b)){return b;}if(leading(a)==leading(b) && a>b){return b;}return a;}"""
    pair("bucket-order", bucket, "int f(int a,int b){if(a>b){return b;}return a;}",
         [(2,13),(16,3),(4,45),(58,72),(93,9),(8,21),(74,7),(19,84)],
         min,"Two positive one- or two-digit integers in a single size-100 bucket. Observe the first returned cell.")
    authored = prefix+"int sum=a[0];for(int i=1;i<n;i++){sum+=a[i];}return sum;}"
    pair("prefix-total-convention", authored, authored.replace("int a[3];","if(n==0){return -17;}int a[3];"),
         [(0,83,-7,4),(1,23,42,15),(2,3,0,9),(3,-4,17,8),(0,-19,28,36),(3,10,24,-2),(2,-7,-8,9)],
         lambda n,*cells:sum(cells[:n]) if n else -17, "A signed active prefix has a distinct empty-result convention.")
    for family, partition, value in [("development-double", "development", 2), ("selection-cube","selection",3)]:
        operator = "*" if value==2 else "+"
        expression = "a*a" if value==2 else "a*a*a"
        pair(family, f"int f(int a){{return a{operator}{value};}}", f"int f(int a){{return {expression};}}",
             [(n,) for n in range(value*10,value*10+7)],lambda a:a**value,f"Authored integer power {value}.",partition)
    return rows


def freeze():
    payload = (json.dumps(fixtures(), indent=2)+"\n").encode()
    (ROOT/"cases-v1.json").write_bytes(payload)
    manifest = dict(case_sha256=sha256(payload).hexdigest(), partitions=dict(Counter(r["partition"] for r in fixtures())),
                    upstream_sha256={p.name:sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/"upstream").iterdir())},
                    revisions_sha256=sha256((ROOT/"revisions.json").read_bytes()).hexdigest())
    (ROOT/"manifest-v1.json").write_text(json.dumps(manifest,indent=2)+"\n")


if __name__=="__main__":
    freeze()
