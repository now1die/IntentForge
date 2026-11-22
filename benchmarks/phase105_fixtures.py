"""Frozen documented defects and separately identified authored controls."""
from bisect import bisect_left, bisect_right
from collections import Counter
from hashlib import sha256
import json
from math import gcd
from pathlib import Path

ROOT = Path(__file__).with_name("phase105_data")
PYTHON, JS, JAVA = ("TheAlgorithms/"+name for name in ("Python","JavaScript","Java"))
EXTERNAL = {
    "iterative-leftmost-match": (PYTHON,"searches/binary_search.py","leftmost",
        "00d9ebb4c0f6e37856b68c4317db43d4d710a775","1d46ea50ec2ef4a615d421c1c1f66cee553465b2",
        "MIT","Five sorted scalar cells. Inline pure current-cell reads and omit the sortedness exception on the already sorted domain."),
    "coprime-zero-operand": (JS,"Maths/CoPrimeCheck.js","coprime",
        "a5945e37c257553bb77cbce95cb6f753ce6d1ab5","8734dfccf90b835b4ca9e09579af4528934a130d",
        "GPL-3.0","Translate Number inputs as bounded signed integers. Preserve the old trial divisor and the fixed shared Euclidean helper."),
    "constant-interpolation-domain": (JAVA,"src/main/java/com/thealgorithms/searches/InterpolationSearch.java","interpolation",
        "fafc5a2964d351b691d05df41994f4e05257cdeb","e57a675893fb6a8fbc725085a3b3039b7565a0b1",
        "MIT","Four ordered cells with either equal values or unique values. The fixed Java long products fit Mini-C int on the documented samples."),
}

ARRAY5 = "int strip[5];strip[0]=a;strip[1]=b;strip[2]=c;strip[3]=d;strip[4]=e;"
ARRAY4 = "int values[4];values[0]=a;values[1]=b;values[2]=c;values[3]=d;"
ARRAY3 = "int cells[3];cells[0]=a;cells[1]=b;cells[2]=c;"

FIRST_HEADER = "int f(int key,int a,int b,int c,int d,int e){"+ARRAY5+"""
    int lo=0;int hi=4;"""
FIRST_LOOP = """while(lo<=hi){int mid=lo+(hi-lo)/2;
        if(strip[mid]==key){EQUALITY}
        else if(key<strip[mid]){hi=mid-1;}else{lo=mid+1;}}
    return FINISH;}"""
FIRST_BEFORE = FIRST_HEADER+FIRST_LOOP.replace("EQUALITY","return mid;").replace("FINISH","-1")
FIRST_AFTER = FIRST_HEADER+"int found=-1;"+FIRST_LOOP.replace("EQUALITY","found=mid;hi=mid-1;").replace("FINISH","found")

ROTATION = "int f(int a,int b,int c){"+ARRAY3+"""
    int left=0;int right=2;
    while(left<right){int middle=left+(right-left)/2;
        if(cells[middle]>cells[right]){left=middle+1;}else{right=middle;}}
    return left;}"""

AGGREGATE = """int combine(int a,int b){int value=0;int bit=1;
    while(a>0 || b>0){if(a%2!=b%2){value+=bit;}a/=2;b/=2;bit*=2;}return value;}
    int f(int a,int b,int c,int d){"""+ARRAY4+"""
    int lowest=a;for(int j=1;j<4;j++){if(values[j]<lowest){lowest=values[j];}}
    int out=0;for(int k=lowest;k<lowest+4;k++){out=combine(out,combine(k,values[k-lowest]));}
    return out;}"""

ZERO = """int f(int quota,int unit){if(unit==0){return -17;}return quota/unit+4;}"""
ADJACENT = "int f(int i,int a,int b,int c){"+ARRAY3+"""
    if(i<0 || i>=2){return -5;}
    if(cells[i]>=cells[i+1]){return cells[i]+8;}return cells[i+1]+2;}"""

UPPER_HEAD = """int endpoint(int key,int lo,int hi,int a,int b,int c,int d){"""+ARRAY4+"""
    if(hi<=lo){return lo;}int mid=(lo+hi)/2;"""
UPPER_TAIL = """if(key>=values[mid]){return endpoint(key,mid+1,hi,a,b,c,d);}
    return endpoint(key,lo,mid,a,b,c,d);}
    int f(int key,int a,int b,int c,int d){return endpoint(key,0,4,a,b,c,d);}"""
UPPER = UPPER_HEAD+UPPER_TAIL
UPPER_FAULT = UPPER_HEAD+"if(key==values[mid]){return mid;}"+UPPER_TAIL.replace("key>=","key>")

ROTATION_INPUTS = [(3,8,1),(5,1,2),(2,5,9),(9,-2,4),(0,4,8),(8,11,-3),(20,5,10)]
UPPER_INPUTS = [(6,1,6,6,9),(3,3,3,3,8),(8,2,4,6,8),(0,1,4,4,9),
                (12,1,4,4,9),(4,3,4,4,5),(11,10,11,11,11)]


def index_of(key,*cells):
    return cells.index(key) if key in cells else -1


def minimum_index(*values):
    return values.index(min(values))


def range_xor(*values):
    low = min(values)
    out = 0
    for value in (*values,*range(low,low+len(values))):
        out ^= value
    return out


def trunc_div(n,d):
    return (1 if n*d>=0 else -1)*(abs(n)//abs(d))


def fixtures():
    rows = []

    def add(family,code,inputs,expect,description,domain,*,fault=None,partition="final",holdout=2):
        vectors = [{"arguments":list(args),"expected":expect(*args)} for args in inputs]
        assert len({tuple(row["arguments"]) for row in vectors})==len(vectors)
        assert 3<=len(vectors)-holdout<=12
        provenance = dict(group="authored",origin="IntentForge Phase 10.5",license="repository license")
        if family in EXTERNAL:
            repo,path,archive,before,after,license_name,adaptation=EXTERNAL[family]
            provenance = dict(group="adapted_real_defect",origin=f"https://github.com/{repo}/commit/{after}",
                              repository=repo,path=path,archive=archive,before=before,after=after,
                              license=license_name,adaptation=adaptation)
        provenance["review"]="Independent executable expected outputs. Human review unavailable."
        common = dict(family=family,partition=partition,compiler_valid=True,requirement=None,
                      specification=description,domain=domain,vectors=vectors[:-holdout],
                      holdout_vectors=vectors[-holdout:],provenance=provenance)
        if fault is not None:
            rows.append(dict(common,id=family+"-fault",source=fault,references=[code],disposition="fault",
                             fault_origin="adapted-real-defect" if family in EXTERNAL else "project-injected"))
        rows.append(dict(common,id=family+"-control",source=code,references=[],disposition="control",fault_origin=None))

    development = "int f(int a,int b){int base=a*b;return base-base/3;}"
    add("development-discount-third",development,[(3,3),(2,3),(-1,9),(1,1),(7,9),(11,3)],
        lambda a,b:a*b-trunc_div(a*b,3),"Subtract a third of a signed product.","Small integers.",
        fault=development.replace("base/3","base/2"),partition="development")
    selection = "int f(int k){int qty=27; for(int j=8;j>=k;j-=3){qty-=j*j;}return qty;}"
    add("selection-remaining-squares",selection,[(8,),(5,),(2,),(9,),(-1,),(6,)],
        lambda n:27-sum(x*x for x in range(8,n-1,-3)),"Deduct the squared sampled positions through the final position.",
        "Small signed lower limits.",fault=selection.replace("j>=k","j>k"),partition="selection")

    add("iterative-leftmost-match",FIRST_AFTER,
        [(4,1,2,4,4,4),(3,3,3,3,8,10),(12,2,3,8,9,12),(7,1,3,5,9,12),
         (0,1,2,2,9,11),(8,-2,1,8,8,12),(15,1,5,7,9,12),(9,1,9,9,9,17)],
        index_of,"Find the first matching occurrence or -1 for an absent key.","Five ordered signed cells.",
        fault=FIRST_BEFORE,holdout=3)

    before = """int legacy_divisor(int a,int b){int less=b;if(a<b){less=a;}
        for(less=less;less>=2;less--){if(a%less==0 && b%less==0){return less;}}return less;}
        bool f(int a,int b){if(a<0){a=-a;}if(b<0){b=-b;}return legacy_divisor(a,b)==1;}"""
    after = """int divisor(int a,int b){if(a<0){a=-a;}if(b<0){b=-b;}
        while(b!=0){int r=a%b;a=b;b=r;}return a;}
        bool f(int a,int b){return divisor(a,b)==1;}"""
    add("coprime-zero-operand",after,[(1,0),(0,-1),(0,0),(7,5),(6,15),(2,0),(0,1),(-10,21)],
        lambda a,b:gcd(a,b)==1,"Return whether the greatest common divisor is one.","Small signed integers.",
        fault=before,holdout=3)

    interp = "int f(int key,int a,int b,int c,int d){"+ARRAY4+"""
        int start=0;int end=3;
        while(start<=end && key>=values[start] && key<=values[end]){
            GUARD
            int pos=start+PROBE;
            if(values[pos]==key){return pos;}
            if(values[pos]<key){start=pos+1;}else{end=pos-1;}}
        return -1;}"""
    add("constant-interpolation-domain",
        interp.replace("GUARD","if(values[start]==values[end]){return start;}")
              .replace("PROBE","((end-start)*(key-values[start]))/(values[end]-values[start])"),
        [(5,5,5,5,5),(4,0,1,2,4),(0,0,1,2,4),(6,1,2,3,4),(-2,-1,0,1,2),
         (2,0,1,2,4),(-3,-3,-3,-3,-3),(11,2,4,8,11)],
        index_of,"Find the target in a constant or strictly increasing interpolation interval.",
        "Four ordered small cells, either all equal or unique.",
        fault=interp.replace("GUARD","").replace("PROBE","((end-start)/(values[end]-values[start]))*(key-values[start])"),holdout=3)

    add("duplicate-upper-endpoint",UPPER,UPPER_INPUTS,lambda key,*cells:bisect_right(cells,key),
        "Return the first position strictly beyond the target, including one-past-end.",
        "Four nondecreasing cells and a signed key.",fault=UPPER_FAULT)
    add("coordinated-three-cell-pivot",ROTATION,ROTATION_INPUTS,minimum_index,
        "Return the minimum index in a distinctly ordered three-cell rotation.",
        "Three distinct cells in cyclic ascending order.",fault=ROTATION.replace("cells[middle]>","cells[middle]<").replace("left=middle+1","left=middle"))
    add("checked-adjacent-score",ADJACENT,[(0,5,5,1),(1,8,9,5),(0,1,3,7),(1,1,3,3),(2,1,9,12),
        (0,-3,-3,8),(1,6,-1,5)],lambda i,*a:-5 if not 0<=i<2 else a[i]+8 if a[i]>=a[i+1] else a[i+1]+2,
        "Choose the earlier cell on equal neighbor values and apply its score bonus.",
        "Three signed values and logical indices zero and one.",fault=ADJACENT.replace("cells[i]>=","cells[i]>"))
    add("division-reserve-sentinel",ZERO,[(35,0),(0,7),(10,5),(-20,4),(9,0),(4,-3),(3,2)],
        lambda a,b:-17 if not b else trunc_div(a,b)+4,"Apply a reserve sentinel for a zero divisor.",
        "Small signed inputs.",fault=ZERO.replace("if(unit==0){return -17;}",""))
    add("shifted-digit-aggregate",AGGREGATE,[(0,3,2,6),(3,7,4,8),(12,9,10,21),(8,3,3,9),(7,5,10,3),
        (25,20,30,21),(5,9,12,0)],range_xor,
        "Combine four observed cells and four integer coordinates starting at the observed minimum by XOR.",
        "Four small nonnegative inputs. Duplicates and noncontiguous observed values are valid.",
        fault=AGGREGATE.replace("int k=lowest","int k=0"))
    add("lower-insertion-control",UPPER.replace("key>=","key>").replace("endpoint","insertion"),
        UPPER_INPUTS,lambda key,*cells:bisect_left(cells,key),"Return the first position at or above the target.",
        "Four nondecreasing signed cells.")
    add("ordinary-duplicate-match",FIRST_BEFORE,[(4,1,4,4,4,9),(3,3,3,3,3,3),(0,1,2,3,4,5),
        (5,1,2,5,8,13),(6,3,4,6,6,9),(9,0,4,9,9,10)],
        lambda key,*a:2 if key in a else -1,"Return the initially checked matching midpoint or an absence sentinel.",
        "Discovery and holdout matches are at the center.")
    add("empty-or-singleton-search",
        "int f(int n,int key,int a){int payload[1];payload[0]=a;if(n==0){return -1;}if(payload[0]==key){return 0;}return -1;}",
        [(0,1,1),(1,3,3),(1,4,3),(0,7,8),(1,14,14),(1,-5,-2)],
        lambda n,k,a:0 if n and k==a else -1,"Search the logical collection of at most one cell.",
        "Logical length zero or one over physical storage of one initialized cell.")
    add("two-cell-duplicate-pivot",
        "int f(int a,int b){int deck[2];deck[0]=a;deck[1]=b;if(deck[0]<=deck[1]){return 0;}return 1;}",
        [(1,1),(3,7),(12,-2),(-3,-8),(2,2),(-7,2)],minimum_index,
        "Return the earliest minimum of the two-cell rotation, including ties.","Two signed cells.")
    add("signed-noncontiguous-origin",
        "int f(int a,int b,int c){"+ARRAY3+"int base=-3;int sum=0;for(int j=base;j<base+3;j++){sum+=cells[j+3]+j*j;}return sum;}",
        [(1,4,9),(-2,-3,2),(0,1,1),(5,0,-7),(2,8,0),(-10,0,7)],lambda *a:sum(a)+14,
        "Weight three deliberate negative positions without requiring contiguous values.","Three signed inputs.")
    return rows


def freeze():
    rows=fixtures()
    payload=(json.dumps(rows,indent=2,ensure_ascii=False)+"\n").encode()
    files={item.name:sha256(item.read_bytes()).hexdigest() for item in sorted((ROOT/"upstream").iterdir())
           if not item.name.startswith(".")}
    (ROOT/"cases-v1.json").write_bytes(payload)
    (ROOT/"manifest-v1.json").write_text(json.dumps(dict(case_sha256=sha256(payload).hexdigest(),
        upstream_sha256=files,partitions=dict(Counter(row["partition"] for row in rows)),
        external_sources={key:list(value) for key,value in EXTERNAL.items()},
        holdout="Discovery synthesis and fresh worker verification are separate.",
        grouping="Upstream repositories and authored families occupy one partition."),indent=2)+"\n")


if __name__=="__main__":
    freeze()
