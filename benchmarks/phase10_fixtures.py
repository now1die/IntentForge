"""Freeze Phase 10 fixture pairs and independent expected outcomes."""
from bisect import bisect_left
from collections import Counter
from hashlib import sha256
from math import gcd, lcm
from pathlib import Path
import json

ROOT = Path(__file__).with_name("phase10_data")
JAVA = "TheAlgorithms/Java"
PYTHON = "TheAlgorithms/Python"
SEARCH = "src/main/java/com/thealgorithms/searches/"
EXTERNAL = {
    "recursive-empty-interval": (PYTHON, "searches/binary_search.py", "recursion",
        "c4234192facc1b13ad3cb7be25dbd829c32fbe2d", "53681f199c46bebeca3c019d91af79c392f570b3",
        "Four ordered cells. Emulate Python floor on the midpoint and map None to -1 and recursion exhaustion to CALL_DEPTH. Exclude keys below the first cell."),
    "zero-lcm": (PYTHON, "maths/least_common_multiple.py", "lcm",
        "d9027b034699aa60f3e89e1344211b686274af27", "4aca14b650a238e4906c3d753b075cc324774e67",
        "Translate the fast LCM implementation on nonnegative integers. Replace the GCD dependency with equivalent iterative arithmetic on this domain."),
    "duplicate-lower-bound": (JAVA, SEARCH+"LowerBound.java", "lower",
        "d9b86d1992b8bd4cadbd832822c792628117e69d", "f8207cc34ca0bd5694cce3120a9741ee50b2d2e8",
        "Translate Comparable values as integers. Five ordered cells and a saturated lower bound preserve the recursive partition and equality shortcut."),
    "short-rotation-pivot": (JAVA, SEARCH+"HowManyTimesRotated.java", "rotated",
        "b33b75b846774274440d7c871e0802e26bed6dc0", "ed2928f659e2424321b51967bc641a24340b69f7",
        "Recreate lengths one, two and five with a checked negative neighbor. Five-cell original samples pivot immediately. Omit original hanging inputs."),
}


def index_of(key,*cells):
    return cells.index(key) if key in cells else -1


def fixtures():
    rows = []

    def add(family, code, inputs, expected, specification, domain, *, fault=None, partition="final", holdout=2):
        vectors = [{"arguments":list(args),"expected":expected(*args)} for args in inputs]
        assert len({tuple(row["arguments"]) for row in vectors}) == len(vectors)
        assert 2 <= len(vectors)-holdout <= 12
        provenance = dict(group="authored", origin="IntentForge Phase 10", license="repository license",
                          review="Independent executable reference. External human review unavailable.")
        if family in EXTERNAL:
            repo,path,archive,parent,revision,adaptation = EXTERNAL[family]
            provenance |= dict(group="adapted_real_defect",origin=f"https://github.com/{repo}/commit/{revision}",
                               repository=repo,path=path,archive=archive,before=parent,after=revision,
                               license="MIT",adaptation=adaptation)
        split = len(vectors)-holdout
        common = dict(family=family,partition=partition,compiler_valid=True,specification=specification,
                      domain=domain,requirement=None,vectors=vectors[:split],holdout_vectors=vectors[split:],
                      provenance=provenance)
        if fault is not None:
            rows.append(dict(common,id=family+"-fault",source=fault,references=[code],disposition="fault",
                             fault_origin="adapted-real-defect" if family in EXTERNAL else "project-injected"))
        rows.append(dict(common,id=family+"-control",source=code,references=[],fault_origin=None,disposition="control"))

    dev = "int f(int x,int y){int n=x*2+y; if(n<-10){return 29;}return 2*n+3;}"
    add("development-cold-reading",dev, [(-9,0),(-8,5),(-5,0),(9,-4),(-20,4),(-3,7)],
        lambda x,y:29 if 2*x+y<-10 else 2*(2*x+y)+3,"Use the cold-reading override.","Small signed readings.",
        fault=dev.replace("n<-10","n<-12"),partition="development")
    sel = "int f(int n){int x=9;for(int j=2;j<=n;j+=3){x-=j;}return x;}"
    add("selection-charged-checkpoints",sel, [(2,),(5,),(8,),(6,),(11,),(0,)],
        lambda n:9-sum(range(2,n+1,3)),"Charge each third checkpoint through the end.","Counts 0–15.",
        fault=sel.replace("j<=n","j<n"),partition="selection")
    cal = "int f(int k,int v){int p=v-3;int sum=0;for(int j=p;j<k;j++){sum+=j*2+5;}return sum;}"
    add("calibration-rebased-count",cal, [(4,6),(7,1),(5,8),(-1,-2),(10,8),(0,2)],
        lambda k,v:sum(2*j+5 for j in range(v-3,k)),"Accumulate from an adjusted starting point.","Small signed counts.",
        fault=cal.replace("j=p","j=0"),partition="calibration")

    cells4 = "int data[4];data[0]=d;data[1]=e;data[2]=g;data[3]=h;"
    recursive = """int locate(int key,int d,int e,int g,int h,int low,int high){"""+cells4+"""
        if(high<low){return -1;}
        int middle=low+(high-low)/2;if((high-low)%2<0){middle--;}
        if(data[middle]==key){return middle;}
        if(data[middle]>key){return locate(key,d,e,g,h,low,middle-1);}
        return locate(key,d,e,g,h,middle+1,high);}
        int f(int key,int d,int e,int g,int h){return locate(key,d,e,g,h,0,3);}"""
    add("recursive-empty-interval",recursive, [(5,1,4,9,13),(4,1,4,9,13),(19,1,4,9,13),(13,1,4,9,13),
        (1,1,4,9,13),(3,-1,2,6,12),(6,-1,2,6,12)],index_of,
        "Return the key position or -1 on an empty search interval.","Four distinct increasing integers with key at least the first.",
        fault=recursive.replace("if(high<low){return -1;}",""))

    euclid = """int divisor(int x,int y){while(y!=0){int r=x%y;x=y;y=r;}return x;}
        int f(int a,int b){if(a==0 || b==0){return 0;}return a/divisor(a,b)*b;}"""
    add("zero-lcm",euclid,[(0,0),(0,5),(6,0),(5,7),(6,8),(3,9),(8,12),(4,0)],lcm,
        "Return the least common multiple, with a zero result if either input is zero.","Small nonnegative operands.",
        fault=euclid.replace("if(a==0 || b==0){return 0;}",""))

    cells5 = "int cell[5];cell[0]=a;cell[1]=b;cell[2]=c;cell[3]=d;cell[4]=e;"
    lower = """int seek(int key,int left,int right,int a,int b,int c,int d,int e){"""+cells5+"""
        if(right<=left){return left;}int m=left+(right-left)/2;
        if(key<=cell[m]){return seek(key,left,m,a,b,c,d,e);}
        return seek(key,m+1,right,a,b,c,d,e);}
        int f(int key,int a,int b,int c,int d,int e){return seek(key,0,4,a,b,c,d,e);}"""
    add("duplicate-lower-bound",lower,[(3,1,3,3,3,8),(5,5,5,5,7,9),(4,2,3,7,8,10),(7,2,3,5,7,7),
        (-2,-2,-2,-2,0,1),(15,1,3,5,7,9),(8,3,8,8,8,9)],
        lambda k,*a:min(4,bisect_left(a,k)),"Return the first element at least the key, or the final index.",
        "Five sorted integer cells, possibly with duplicates.",
        fault=lower.replace("if(key<=cell[m])","if(key==cell[m]){return m;}if(key<cell[m])"))

    rotate_header = "int f(int n,int a,int b,int c,int d,int e){"+cells5+"int low=0;int high=n-1;"
    rotate = rotate_header+"""while(low<high){int middle=low+(high-low)/2;
        if(cell[middle]>cell[high]){low=middle+1;}else{high=middle;}}return low;}"""
    rotate_fault = rotate_header+"""int middle=0;while(low<=high){middle=low+(high-low)/2;
        if(cell[middle]<cell[middle-1]&&cell[middle]<cell[middle+1]){break;}
        else if(cell[middle]>cell[middle-1]&&cell[middle]<cell[middle+1]){high=middle+1;}
        else if(cell[middle]>cell[middle-1]&&cell[middle]>cell[middle+1]){low=middle-1;}}
        return middle;}"""
    add("short-rotation-pivot",rotate,[(1,5,0,0,0,0),(2,12,2,0,0,0),(5,5,7,1,3,4),
        (5,11,21,-2,4,9),(1,-10,0,0,0,0),(2,-5,3,0,0,0),(5,6,8,-9,-5,1)],
        lambda n,*a:min(range(n),key=a.__getitem__),"Return the minimum position in the rotated sorted prefix.",
        "Distinct rotated cells. Length one, two, or five with pivot two on the longer samples.",fault=rotate_fault)

    fixed = "int f(int p,int d,int e,int g,int h){"+cells4+"return 3*data[p+1]-2;}"
    add("lookahead-calibration-cell",fixed,[(2,6,5,-1,9),(1,4,-8,10,12),(0,9,17,11,13),
        (2,-5,3,6,2),(0,2,7,4,6),(2,2,-5,-7,-9)],
        lambda p,*a:3*a[p+1]-2,"Calibrate from the next physical cell.","Logical indices zero through two.",
        fault=fixed.replace("p+1","p+2"))

    iteration = """int f(int key,int d,int e,int g,int h){"""+cells4+"""
        if(key<data[0]){return -19;}int p=0;int q=3;
        while(q>=p){int pivot=p+(q-p)/2;
        if(data[pivot]==key){return pivot;}
        if(key<data[pivot]){q=pivot-1;}else{p=pivot+1;}}
        return -19;}"""
    add("inclusive-ceiling-lookup",iteration,[(15,2,4,7,11),(11,2,4,7,11),(2,2,4,7,11),(6,2,4,7,11),
        (7,2,4,7,11),(32,-9,3,12,26),(23,2,8,17,23)],
        lambda k,*a:a.index(k) if k in a else -19,"Inclusive array lookup with -19 absent sentinel.",
        "Four distinct increasing integers.",fault=iteration.replace("int q=3","int q=4"))

    origin = """int f(int a,int b,int c){int cell[3];cell[0]=a;cell[1]=b;cell[2]=c;
        int low=a;for(int v=1;v<3;v++){if(cell[v]<low){low=cell[v];}}
        int out=5;for(int i=low;i<low+3;i++){out+=2*cell[i-low]+i;}return out;}"""
    add("minimum-rebased-grid",origin,[(0,4,5),(5,-2,8),(4,2,3),(7,9,11),(-1,8,3),(8,4,-3),(8,7,8)],
        lambda *a:8+2*sum(a)+3*min(a),"Accumulate weighted values from the computed minimum coordinate.",
        "Three small signed cells.",fault=origin.replace("cell[i-low]","cell[i-0]"))

    helper = """int reduce(int x,int y){while(y!=0){int rem=x%y;x=y;y=rem;}return x;}
        int f(int n,int p){int total=7;for(int t=2;t<=n;t+=2){
        if(t<p){continue;}if(reduce(n,t)==2){total+=t+1;}}return total;}"""
    add("even-gcd-weight",helper,[(6,2),(10,4),(14,5),(12,2),(9,3),(16,6),(18,8)],
        lambda n,p:7+sum(t+1 for t in range(2,n+1,2) if t>=p and gcd(n,t)==2),
        "Sum even checkpoint weight when the common divisor is two.","Small positive n and cutoff.",
        fault=helper.replace("reduce(n,t)==2","reduce(n,t)!=2"))

    growth = """int f(int key,int a,int b,int c,int d,int e){"""+cells5+"""
        if(key==cell[0]){return 0;}int width=1;
        while(width<5 && cell[width]<key){width*=3;}
        int lo=width/3;int hi=width+1;if(hi>5){hi=5;}hi--;
        while(lo<=hi){int m=lo+(hi-lo)/2;if(cell[m]==key){return m;}
        if(key>cell[m]){lo=m+1;}else{hi=m-1;}}
        return -23;}"""
    add("tripled-window-handoff",growth,[(4,2,4,7,9,13),(9,2,4,7,9,13),(7,2,4,7,9,13),
        (8,2,4,7,9,13),(13,2,4,7,9,13),(32,-3,2,5,8,23),(15,3,5,9,15,24)],
        lambda k,*a:a.index(k) if k in a else -23,"Lookup in a tripled window with a stable absent sentinel.",
        "Five distinct increasing integers.",fault=growth.replace("hi=width+1","hi=width").replace("return -23","return -lo-23"))

    add("intentional-descending-offset", "int f(int x,int d,int e,int g,int h){"+cells4+
        "int out=0;for(int p=x;p>=1;p--){out+=data[p];}return out;}",
        [(0,2,3,6,7),(1,2,4,6,8),(3,-7,2,3,4),(2,8,2,4,-8),(2,1,0,4,5),(3,0,6,1,7)],
        lambda n,*a:sum(a[1:n+1]),"Reverse traversal excludes the zeroth metadata cell.","Indices zero through three.")
    add("fixed-singleton-preset", "int f(int x,int d){int table[1];table[0]=d;if(x==table[0]){return 0;}return -13;}",
        [(3,6),(3,3),(7,12),(2,2),(-12,-12),(8,6)],lambda x,d:0 if x==d else -13,
        "One-cell lookup with a deliberate absent result.","Small signed integers.")
    add("unobserved-short-circuit", "int f(int a,int b){int table[2];table[0]=a;table[1]=b;"
        "if(a!=0 && table[1]/a>0){return table[1];}return table[0];}",
        [(0,1),(0,-1),(3,9),(2,-1),(-5,-11),(-8,1)],lambda a,b:b if a and b*a>0 and abs(b)>=abs(a) else a,
        "Guard the quotient and preserve the inactive result.","Small signed integer pairs.")
    half = recursive.replace("high<low","high<=low").replace("middle-1","middle").replace("0,3","0,4")
    add("half-open-recursive-control",half,[(10,1,2,4,6),(6,1,2,4,6),(1,1,2,4,6),
        (4,1,2,4,6),(0,-2,0,5,12),(-3,-2,0,5,12)],index_of,
        "The upper endpoint is exclusive in the recursive search.","Four distinct increasing cells.")
    return rows


def freeze():
    rows = fixtures()
    payload = (json.dumps(rows,indent=2,ensure_ascii=False)+"\n").encode()
    hashes = {item.name:sha256(item.read_bytes()).hexdigest() for item in sorted((ROOT/"upstream").iterdir())
              if not item.name.startswith(".")}
    (ROOT/"cases-v1.json").write_bytes(payload)
    (ROOT/"manifest-v1.json").write_text(json.dumps(dict(
        case_sha256=sha256(payload).hexdigest(),upstream_sha256=hashes,
        partitions=dict(Counter(row["partition"] for row in rows)),
        external_sources={key:list(value) for key,value in EXTERNAL.items()},
        grouping="One split per repository and family. Archived misses are diagnostic only.",
        holdout="Discovery generates candidates. Held-out vectors are separate verification requests."
    ),indent=2)+"\n")


if __name__=="__main__":
    freeze()
