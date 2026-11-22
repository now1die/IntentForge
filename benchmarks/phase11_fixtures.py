"""Independent Phase 11 specimens and separately authored control cases."""
from collections import Counter
from hashlib import sha256
import json
from math import gcd
from pathlib import Path

ROOT = Path(__file__).with_name("phase11_data")
PYTHON, JS, JAVA = ("TheAlgorithms/"+language for language in ("Python","JavaScript","Java"))
EXTERNAL = {
    "exponential-negative-endpoint":(PYTHON,"searches/exponential_search.py","exponential",
        "de56f294c8658112d7782b9ccd675dd0e12eb49f","d81528a928048ffe34fe3553b96645991bd5d1fa",
        "MIT","Five sorted unique scalar cells. A wrapper supplies explicit bounds and the old recursive reset is preserved. Python recursion exhaustion maps to CALL_DEPTH."),
    "empty-numeric-mean":(JS,"Maths/AverageMean.js","mean",
        "3f52add84d4431cb352657206750741d8b0a6ca4","19ecb18f0af35a83542410e59c16975bd8ddd4c3",
        "GPL-3.0","Small numeric prefixes. Exact integer means only. NaN maps to DIVISION_BY_ZERO and the documented empty-input rejection maps to -912."),
    "single-row-column-end":(JAVA,"src/main/java/com/thealgorithms/searches/BinarySearch2dArray.java","row",
        "51a0156d8431f1e93021fa9a3dd6ef0533d04880","0a76bf8db406f8c6b6569cd83bfc31b3e118460f",
        "MIT","The public one-row path is flattened into fixed cells. The return column is preserved and Java bounds errors map to ARRAY_BOUNDS."),
}
FIVE = "int shelf[5];shelf[0]=a;shelf[1]=b;shelf[2]=c;shelf[3]=d;shelf[4]=e;"
FOUR = "int bins[4];bins[0]=a;bins[1]=b;bins[2]=c;bins[3]=d;"
SIX = "int tape[6];tape[0]=a;tape[1]=b;tape[2]=c;tape[3]=d;tape[4]=e;tape[5]=g;"
INTERPOLATE = "int f(int target,int a,int b,int c,int d,int e){"+FIVE+"""
    int left=0;int right=4;
    while(left<=right && shelf[left]<=target && target<=shelf[right]){
        if(shelf[right]==shelf[left]){return left;}
        int probe=left+((right-left)*(target-shelf[left]))/(shelf[right]-shelf[left]);
        if(target==shelf[probe]){return probe;}
        if(target>shelf[probe]){left=probe+1;}else{right=probe-1;}}
    return -23;}"""
INTERPOLATE_FAULT = INTERPOLATE.replace("if(shelf[right]==shelf[left]){return left;}","").replace(
    "((right-left)*(target-shelf[left]))/(shelf[right]-shelf[left])",
    "((right-left)/(shelf[right]-shelf[left]))*(target-shelf[left])")

CYCLIC = "int f(int a,int b,int c,int d,int e,int g){"+SIX+"""
    int lo=0;int hi=5;
    while(lo<hi){int middle=lo+(hi-lo)/2;
      if(tape[middle]>tape[hi]){lo=middle+1;}
      else if(tape[middle]==tape[hi]){hi--;}else{hi=middle;}}
    return lo;}"""
CYCLIC_FAULT = CYCLIC.replace("else if(tape[middle]==tape[hi]){hi--;}","")
CYCLIC_ROWS = [(4,4,4,1,3,4),(7,7,7,7,2,6),(1,2,3,5,5,5),(10,10,10,2,10,10),(5,5,5,5,5,5),
               (2,2,2,-6,0,2),(8,8,8,8,1,8)]
XOR = """int blend(int p,int q){int out=0;int bit=1;while(p>0 || q>0){
    if(p%2!=q%2){out+=bit;}p/=2;q/=2;bit*=2;}return out;}"""
RANGE = XOR+"int f(int a,int b,int c,int d){"+FOUR+"""
    int from=a;for(int j=1;j<4;j++){if(bins[j]<from){from=bins[j];}}
    int computed=9;for(int k=from;k<from+4;k++){computed=blend(computed,blend(k+1,bins[k-from]));}
    return computed;}"""
RANGE_FAULT = RANGE.replace("int k=from","int k=0").replace("bins[k-from]","bins[k-0]")
HELPER = """int magnitude(int a,int b){if(a<0){a=-a;}if(b<0){b=-b;}
    while(b!=0){int rest=a%b;a=b;b=rest;}return a;}
    bool f(int a,int b){if(a==0 || b==0){return a==1 || a==-1 || b==1 || b==-1;}
    return magnitude(a,b)==1;}"""
HELPER_FAULT = HELPER.replace("if(a==0 || b==0){return a==1 || a==-1 || b==1 || b==-1;}",
                              "if(a==0 || b==0){return false;}")

def find(key,*cells):
    return cells.index(key) if key in cells else -1


def xor_range(*cells):
    value=9
    for index,cell in enumerate(cells,min(cells)):
        value ^= (index+1)^cell
    return value


def fixtures():
    rows = []

    def add(family,code,inputs,expected,description,domain,*,fault=None,partition="final",holdout=2):
        vectors=[{"arguments":list(args),"expected":expected(*args)} for args in inputs]
        assert len({tuple(row["arguments"]) for row in vectors})==len(vectors)
        assert 3<=len(vectors)-holdout<=12
        provenance=dict(group="authored",origin="IntentForge Phase 11",license="repository license")
        if family in EXTERNAL:
            repo,path,archive,before,after,license_name,adaptation=EXTERNAL[family]
            provenance=dict(group="adapted_real_defect",origin=f"https://github.com/{repo}/commit/{after}",repository=repo,
                            path=path,archive=archive,before=before,after=after,license=license_name,adaptation=adaptation)
        provenance["review"]="Independent executable expected outputs. Human review unavailable."
        common=dict(family=family,partition=partition,compiler_valid=True,requirement=None,specification=description,
                    domain=domain,vectors=vectors[:-holdout],holdout_vectors=vectors[-holdout:],provenance=provenance)
        if fault is not None:
            rows.append(dict(common,id=family+"-fault",source=fault,references=[code],disposition="fault",
                             fault_origin="adapted-real-defect" if family in EXTERNAL else "project-injected"))
        rows.append(dict(common,id=family+"-control",source=code,references=[],disposition="control",fault_origin=None))

    development="int f(int n,int z){int fee=n*3;if(n<z){return fee+8;}return fee-8;}"
    add("development-switch-fee",development,[(3,4),(2,2),(-5,-4),(9,3),(7,9),(5,-1)],
        lambda n,z:n*3+(8 if n<z else -8),"Switch the fee before the exclusive threshold.","Small signed scalar inputs.",
        fault=development.replace("n<z","n<=z"),partition="development")
    selection="int f(int n,int c){int total=c;for(int j=1;j<=n;j+=2){total+=5*j-2;}return total;}"
    add("selection-odd-invoice",selection,[(1,8),(3,4),(4,1),(0,2),(7,5),(8,0)],
        lambda n,c:c+sum(5*j-2 for j in range(1,n+1,2)),"Sum odd checkpoints with a base charge.",
        "Nonnegative small counts and signed charges.",fault=selection.replace("j<=n","j<n"),partition="selection")

    expo="""int search(int key,int a,int b,int c,int d,int e,int lo,int hi){"""+FIVE+"""
        RESET
        if(hi<lo){return -1;}int mid=lo+(hi-lo)/2;
        if(shelf[mid]==key){return mid;}
        if(shelf[mid]>key){return search(key,a,b,c,d,e,lo,mid-1);}
        return search(key,a,b,c,d,e,mid+1,hi);}
        int f(int key,int a,int b,int c,int d,int e){"""+FIVE+"""
            if(shelf[0]==key){return 0;}
            int span=1;while(span<5 && shelf[span]<key){span*=2;}
            int end=span;if(end>4){end=4;}return search(key,a,b,c,d,e,span/2,end);}"""
    add("exponential-negative-endpoint",expo.replace("RESET",""),[(0,1,4,8,12,17),(1,1,4,8,12,17),(17,1,4,8,12,17),
        (23,1,4,8,12,17),(6,1,4,8,12,17),(-12,-7,0,3,5,9),(5,-7,0,3,5,9),(0,-7,0,3,5,9)],
        find,"Find the exact unique key after expanding the search window.",
        "Five distinct increasing signed values.",fault=expo.replace("RESET","if(hi<0){hi=4;}"),holdout=3)
    mean="int f(int n,int a,int b,int c,int d){"+FOUR+"""
        if(n==0){return -912;}int total=0;for(int j=0;j<n;j++){total+=bins[j];}
        return total/n;}"""
    add("empty-numeric-mean",mean,[(0,0,0,0,0),(2,2,6,21,21),(4,1,5,7,3),(1,-8,2,3,4),(3,3,6,9,21),
        (0,5,7,10,11),(2,-3,3,9,11),(4,-3,-7,-9,-1)],
        lambda n,*a:sum(a[:n])//n if n else -912,"Return the integral mean or the normalized empty-input rejection.",
        "Integer-valued means of bounded signed prefixes.",fault=mean.replace("if(n==0){return -912;}",""),holdout=3)
    single="int f(int target,int a,int b,int c,int d){"+FOUR+"""
        int left=0;int right=3;while(left<=right){int middle=left+(right-left)/2;
        if(bins[middle]==target){return middle;}if(bins[middle]<target){left=middle+1;}else{right=middle-1;}}
        return -1;}"""
    add("single-row-column-end",single,[(19,1,4,9,15),(15,1,4,9,15),(1,1,4,9,15),(8,1,4,9,15),(0,1,4,9,15),
        (22,-2,4,9,21),(4,-2,4,9,21),(-12,-2,4,9,21)],
        find,"Return the target column in a one-row matrix or -1 if absent.",
        "One row with four distinct ordered columns.",fault=single.replace("right=3","right=4"),holdout=3)

    add("equal-endpoint-probe",INTERPOLATE,[(2,2,2,2,2,2),(9,0,3,4,7,9),(1,1,3,5,7,9),(15,1,3,5,7,9),
        (-6,-5,-3,0,4,8),(8,-1,2,4,8,17),(7,7,7,7,7,7),(12,1,3,6,12,15)],
        lambda k,*a:next((i for i,value in enumerate(a) if value==k),-23),
        "Find the target or return the absence sentinel under guarded interpolation.",
        "Five ordered cells, all equal or all distinct.",fault=INTERPOLATE_FAULT,holdout=3)
    add("duplicate-cyclic-pivot",CYCLIC,CYCLIC_ROWS,lambda *a:a.index(min(a)),
        "Locate the minimum in a cyclically ordered array with repeated nonminimum values.",
        "Six signed cells with a unique minimum, or all equal.",fault=CYCLIC_FAULT)
    add("linked-aggregate-origin",RANGE,[(0,1,4,9),(3,9,4,12),(8,12,5,9),(1,2,1,3),(7,6,9,8),
        (11,20,31,17),(4,0,2,25)],xor_range,
        "Fold the observed cells and the four coordinates above their minimum into a signed-safe XOR total.",
        "Small nonnegative values, including duplicates and gaps.",fault=RANGE_FAULT)

    # The positive helper grammar executes its original bounded trial
    # computation, while the reference guards the same boolean meaning.
    legacy = """int smaller_divisor(int a,int b){if(a<0){a=-a;}if(b<0){b=-b;}int q=a;if(b<a){q=b;}
        for(q=q;q>=2;q--){if(a%q==0 && b%q==0){return q;}}return q;}
        bool f(int a,int b){GUARD return smaller_divisor(a,b)==1;}"""
    guard = "if(a==0 || b==0){return a==1 || a==-1 || b==1 || b==-1;}"
    add("signed-unity-boundary",legacy.replace("GUARD",guard),[(0,1),(-1,0),(0,6),(5,9),(6,9),(0,0),(7,4),
        (0,-1),(1,0),(0,-4)],lambda a,b:gcd(a,b)==1,
        "Return whether magnitudes share only the unit divisor, including signed boundary inputs.",
        "Small signed magnitudes.",fault=legacy.replace("GUARD",""),holdout=3)
    add("helper-zero-output-control",HELPER,[(1,0),(0,-1),(0,6),(7,9),(8,6),(0,0),(3,8)],
        lambda a,b:gcd(a,b)==1,"Use signed magnitude and an explicit unity boundary.","Small signed integers.")
    add("logical-cyclic-singleton",
        "int f(int n,int a,int b){int strip[2];strip[0]=a;strip[1]=b;if(n==0){return -4;}if(n==1 || strip[0]<=strip[1]){return 0;}return 1;}",
        [(0,1,0),(1,8,0),(2,5,5),(2,9,-1),(2,-8,4),(1,-6,-7),(0,12,11)],
        lambda n,a,b:-4 if n==0 else 0 if n==1 or a<=b else 1,
        "Return a minimum coordinate for zero, one or two logical cells.",
        "Two physical cells, prefix length zero through two.")
    add("signed-range-origin",
        "int f(int a,int b,int c,int d){"+FOUR+"int base=-2;int sum=4;for(int k=base;k<base+4;k++){sum+=bins[k+2]*(k+1);}return sum;}",
        [(1,4,9,3),(-2,-3,2,1),(0,1,1,1),(5,0,-7,8),(2,8,0,5),(-10,0,7,8)],
        lambda *a:4+sum(x*w for x,w in zip(a,(-1,0,1,2))),
        "Fold deliberate negative coordinates without an ordering assumption.","Four signed cells.")
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
        holdout="Fresh worker verification with generation disabled.",
        grouping="Upstream repositories and authored families occupy one partition."),indent=2)+"\n")


if __name__=="__main__":
    freeze()
