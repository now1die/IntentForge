"""Frozen real-defect adaptations and separately labeled control cohorts."""
from collections import Counter
from datetime import date
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).with_name("phase95_data")
JAVA = "TheAlgorithms/Java"
JS = "TheAlgorithms/JavaScript"
SEARCH = "src/main/java/com/thealgorithms/searches/"
EXTERNAL = {
    "exclusive-multiple-sum": (JS,"Project-Euler/Problem1.js","multiples",
        "cedab196e7da0a48859baba4839e8ef0dd4aba46","90891b56578d7ae6ac4c8a255da507db613bc6f5",
        "Translate the extracted numeric function to int32 and omit its CLI. Preserve the inclusive defective loop."),
    "gregorian-day-difference": (JS,"Conversions/DateDayDifference.js","date",
        "2fe0dfde23b1179a6fa5fdd7425a3f2bf303d538","f13eec1bbb94484912d10a4e5376aacf533b3de6",
        "Pass components as signed integer arguments for valid dates. Use exact rational scaling for the old floor and integer truncation of each positive term for the fix."),
    "recursive-search-upper-bound": (JAVA,SEARCH+"BinarySearch.java","binary",
        "69d0070c99453f0a5d4793d41aa5d750a5a4a5de","d22420fea8d7b05d02e42111d9bc5e24137e907f",
        "Use five sorted unique integer cells, rebuilt in the recursive frame. Preserve the inclusive upper bound and map index failures to Mini-C ARRAY_BOUNDS."),
    "expanding-search-boundary": (JAVA,SEARCH+"ExponentialSearch.java","exponential",
        "171bdc5cb06df69d9070d5ed1f95a3544a4276e9","55f551b17bd0c48b7cb1ba7ecfb7092803c7a150",
        "Use five sorted unique cells. Translate doubling and exclusive binary-search limits, including Java's raw negative insertion-point result before the fix."),
    "smith-composite-domain": (JAVA,"src/main/java/com/thealgorithms/maths/SmithNumber.java","smith",
        "b42e5df87251019f8836b2799ced4c6e20c4c6f8","e79b0f106477774020d4c5c2738f0854ff3d2444",
        "Translate digit sums, trial division and composite admission for bounded integers. The long product and int32 product agree on the checked sample domain."),
}


def prime(n):
    return n>1 and all(n%i for i in range(2,n))


def smith(n):
    if n<4 or prime(n):
        return False
    def digits(value):
        return sum(map(int,str(value)))
    factors = []
    original = n
    for factor in range(2,n+1):
        while n%factor==0:
            n//=factor
            factors.append(factor)
        if n==1:
            break
    return sum(map(digits,factors))==digits(original)


def index_of(key,*values):
    return values.index(key) if key in values else -1


def fixtures():
    rows=[]
    def add(family,code,inputs,expected,spec,domain,mutation=None,*,fault=None,partition="final",holdout=2):
        vectors=[{"arguments":list(args),"expected":expected(*args)} for args in inputs]
        split=len(vectors)-holdout
        assert 1<split<=12 and len({tuple(row["arguments"]) for row in vectors})==len(vectors),family
        provenance=dict(group="authored",origin="IntentForge Phase 9.5",license="repository license",
                        review="Independent executable reference. External human review unavailable.")
        if family in EXTERNAL:
            repo,path,archive,parent,revision,translation=EXTERNAL[family]
            provenance |= dict(group="adapted_real_defect",origin=f"https://github.com/{repo}/commit/{revision}",
                 repository=repo,path=path,archive=archive,before=parent,after=revision,license="MIT" if repo==JAVA else "GPL-3.0",adaptation=translation)
        common=dict(family=family,partition=partition,compiler_valid=True,specification=spec,domain=domain,requirement=None,
                    vectors=vectors[:split],holdout_vectors=vectors[split:],provenance=provenance)
        if mutation:
            old,new=mutation
            assert code.count(old)==1
            fault=code.replace(old,new)
        if fault:
            rows.append(dict(common,id=family+"-fault",source=fault,references=[code],disposition="fault",
                      fault_origin="adapted-real-defect" if family in EXTERNAL else "project-injected"))
        rows.append(dict(common,id=family+"-control",source=code,references=[],fault_origin=None,
                         disposition="control" if holdout else "ambiguous"))

    add("development-upper-limit","int f(int signal){if(signal>7){return -8;}return signal*signal+1;}",
        [(8,),(9,),(7,),(5,),(11,),(2,)],lambda n:n*n+1 if n<=7 else -8,
        "Above seven return a sentinel, otherwise report a squared measurement.","Signals -15 to 20.",
        ("if(signal>7){return -8;}",""),partition="development")
    add("selection-missed-suffix","int f(int n){int cost=2;for(int j=1;j<=n;j+=2){cost+=j*2;}return cost;}",
        [(1,),(3,),(4,),(0,),(7,),(8,)],lambda n:2+sum(j*2 for j in range(1,n+1,2)),
        "Visit odd checked checkpoints through the closing endpoint.","Counts 0 to 20.",
        ("j<=n","j<n"),partition="selection")
    add("calibration-independent-offset","int f(int a,int k){int a0=a+2;int visits=0;for(int i=0;i<k;i++){visits+=i+1;}return a0+visits;}",
        [(1,3),(4,7),(5,6),(0,2),(-3,4),(9,11)],lambda a,k:a+2+sum(i+1 for i in range(k)),
        "Accumulate weighted zero-origin offsets and add a distinct baseline.","Small signed baselines and nonnegative bounds.",
        ("int i=0","int i=1"),partition="calibration")

    multiples="int f(int n){int total=0;for(int i=0;i<n;i++){if(i%3==0 || i%5==0){total+=i;}}return total;}"
    add("exclusive-multiple-sum",multiples,[(6,),(10,),(15,),(11,),(4,),(30,),(49,)],
        lambda n:sum(set(range(0,n,3))|set(range(0,n,5))),
        "Sum nonnegative multiples of three or five strictly below the bound.","Nonnegative bounds up to 60.",
        fault=multiples.replace("i<n","i<=n"))

    header = """bool leap(int y){if(y%400==0){return true;}if(y%100==0){return false;}return y%4==0;}
    int ordinal(int d,int m,int y){int u=y-1;int shift=0;
      if(m>2){shift=-2;if(leap(y)){shift=-1;}}
      return 365*u+d+shift+"""
    footer = """;}
    int f(int d,int m,int y,int e,int w,int z){int a=ordinal(d,m,y);int b=ordinal(e,w,z);
      if(a<b){return b-a;}return a-b;}"""
    add("gregorian-day-difference",header+"u/4-u/100+u/400+(367*m-362)/12"+footer,
        [(17,8,2002,10,10,2020),(18,2,2001,16,3,2022),(11,11,2011,12,12,2012),
         (1,1,2001,16,3,2011),(29,2,2024,4,3,2024),(4,3,2023,4,3,2024),(30,12,1899,2,1,1900)],
        lambda d,m,y,e,w,z:abs((date(z,w,e)-date(y,m,d)).days),
        "Absolute Gregorian day difference.","Valid dates in years 1800 through 2050.",
        fault=header+"(300*u-12*u+3*u+100*(367*m-362))/1200"+footer)

    array = "int values[5]; values[0]=a;values[1]=b;values[2]=c;values[3]=d;values[4]=e;"
    binary = "int at(int target,int lo,int hi,int a,int b,int c,int d,int e){"+array+"""
      if(hi<lo){return -1;}int mid=(lo+hi)/2;int value=values[mid];
      if(target==value){return mid;}
      if(target<value){return at(target,lo,mid-1,a,b,c,d,e);}return at(target,mid+1,hi,a,b,c,d,e);}
    int f(int key,int a,int b,int c,int d,int e){return at(key,0,4,a,b,c,d,e);}"""
    add("recursive-search-upper-bound",binary,
        [(20,1,3,7,10,18),(7,1,3,7,10,18),(18,1,3,7,10,18),(0,1,3,7,10,18),
         (37,-3,2,5,33,36),(11,-2,0,3,11,50),(5,4,7,9,11,13)],
        index_of,"Find the index of a unique key by recursive binary search.",
        "Five strictly ascending small integers and a signed key.",fault=binary.replace("at(key,0,4","at(key,0,5"))

    exp = "int f(int key,int a,int b,int c,int d,int e){"+array+"""
        if(a==key){return 0;}if(e==key){return 4;}
        int extent=1;while(extent<5 && values[extent]<key){extent*=2;}
        int lo=extent/2;int hi=extent+1;if(hi>5){hi=5;}hi--;
        while(lo<=hi){int mid=(lo+hi)/2;if(values[mid]==key){return mid;}
          if(values[mid]<key){lo=mid+1;}else{hi=mid-1;}}
        return -1;}"""
    add("expanding-search-boundary",exp,[(3,1,3,7,10,18),(7,1,3,7,10,18),(4,1,3,7,10,18),
        (10,1,3,7,10,18),(18,1,3,7,10,18),(-2,-9,-2,3,15,17),(20,1,4,9,17,31),(30,1,5,8,10,15)],
        index_of,"Find the index of a key using a doubled search range.",
        "Five unique sorted integers with a bounded signed search key.",
        fault=exp.replace("hi=extent+1","hi=extent").replace("return -1;}","return -lo-1;}"))

    smith_header = """int digits(int n){if(n<0){n=-n;}int sum=0;while(n!=0){sum+=n%10;n/=10;}return sum;}
    bool prime(int n){if(n<=1){return false;}for(int i=2;i*i<=n;i++){if(n%i==0){return false;}}return true;}
    int factors(int n){int sum=0;int original=n;for(int i=2;i*i<=n;i++){while(n%i==0){sum+=digits(i);n/=i;}}
      if(n>1){sum+=digits(n);}return sum;}
    bool f(int n){if(n<=3 || prime(n)){return false;}return digits(n)==factors(n);}"""
    add("smith-composite-domain",smith_header,[(0,),(4,),(22,),(1,),(2,),(8,),(-4,),(85,),(94,),(100,)],
        smith,"A composite is Smith when its digit sum agrees with the digit sums of its prime factors.",
        "Integers -100 through 100. The int32 and widened trial bounds agree on these samples.",
        fault=smith_header.replace("i*i<=n;i++){while","i*i<=original;i++){while").replace("n<=3 || prime(n)","prime(n)"))

    add("negative-gauge-baseline","int f(int reading,int bias){if(reading<-3){return 17;}return 4*(reading-bias)+10;}",
        [(-5,2),(-4,1),(-3,5),(5,3),(0,9),(-9,-2),(15,6)],
        lambda x,b:17 if x<-3 else 4*(x-b)+10,
        "Return the disabled gauge value before the certified lower point.","Signed readings and bias.",
        ("if(reading<-3){return 17;}",""))
    add("upper-clock-preset","int f(int ticks){if(ticks>11){return -7;}return 53-ticks*4;}",
        [(12,),(14,),(11,),(7,),(0,),(19,),(10,),(13,)],lambda x:53-x*4 if x<=11 else -7,
        "Use the overflow preset after tick eleven.","Tick sample interval 0–20.",("if(ticks>11){return -7;}",""))
    add("boolean-marker-gate","bool f(int mark){if(mark<4){return false;}return mark%4==0 || mark%7==0;}",
        [(0,),(1,),(4,),(7,),(13,),(-4,),(8,),(23,)],lambda n:n>=4 and any(n%d==0 for d in (4,7)),
        "Namespaced markers become active at four and are selected by two independent periods.",
        "Small signed marker values.",("if(mark<4){return false;}",""))

    slides="""int f(int n,int a,int b,int c,int d,int e){int input[5];
      input[0]=a;input[1]=b;input[2]=c;input[3]=d;input[4]=e;
      int best=99;for(int start=0;start<=n-3;start++){int cost=0;
      for(int j=0;j<3;j++){cost+=input[start+j];}
      if(cost<best){best=cost;}}return best;}"""
    add("minimum-filter-window",slides,[(3,5,7,4,8,9),(4,7,1,2,-7,8),(5,9,5,8,1,-3),(2,1,-2,3,2,-1),
        (4,3,5,-2,0,0),(5,-2,-1,7,7,3),(3,4,1,0,2,7)],
        lambda n,*vals:min((sum(vals[i:i+3]) for i in range(n-2)),default=99),
        "Find the least energy of a complete three-sample window.","n 0–5, bounded signed signals.",
        ("start<=n-3","start<n-3"))
    add("marked-tail-sentinel",
        "int f(int lo,int end,int tag){int picked=-71;for(int i=lo;i<=end;i++){if(i%5==tag){picked=i;break;}}return picked;}",
        [(1,3,3),(6,9,4),(1,4,2),(8,6,1),(3,3,3),(17,23,0),(4,5,0)],
        lambda a,b,t:next((i for i in range(a,b+1) if i%5==t),-71),
        "Return the first selected position through the closed endpoint, or a sentinel.",
        "Nonnegative bounds and tag 0–4.",("i<=end","i<end"))
    add("helper-gated-tail",
        """bool parity(int k,int t){if(k<0){return false;}return k%3==t;}
        int f(int first,int last,int skip,int tag){for(int p=first;p<=last;p++){
          if(p==skip){continue;}if(parity(p,tag)){return p;}}return -13;}""",
        [(0,3,0,0),(2,5,2,2),(4,7,5,0),(-2,1,0,0),(8,8,7,2),(8,15,10,1),(1,4,2,1)],
        lambda a,b,s,t:next((i for i in range(a,b+1) if i>=0 and i!=s and i%3==t),-13),
        "Select the first non-skipped checkpoint satisfying a helper's typed condition.",
        "Small signed checkpoints and residue 0–2.",("p<=last","p<last"))
    add("weighted-derived-origin",
        """int start(int cap,int margin){if(cap<margin){return cap-2;}return margin-2;}
        int f(int cap,int margin,int end){int from=start(cap,margin);int pay=1;for(int i=from;i<end;i++){pay+=3*i+1;}return pay;}""",
        [(5,8,9),(1,4,5),(8,2,7),(3,6,1),(7,4,9),(-2,5,6),(8,11,4)],
        lambda a,b,k:1+sum(3*i+1 for i in range(min(a,b)-2,k)),
        "Accumulate weighted positions from the lower adjusted input.","Small signed endpoints and bounded iteration.",
        ("int i=from","int i=0"))
    add("descending-margin-origin",
        """int f(int upper,int offset,int end){int first=upper+offset;int n=-9;
        for(int i=first;i>=end;i-=2){n+=i+8;}return n;}""",
        [(4,2,0),(8,3,1),(0,0,0),(3,0,4),(-3,-1,-7),(6,2,0),(2,-2,-3)],
        lambda a,b,k:-9+sum(i+8 for i in range(a+b,k-1,-2)),
        "Use the sum-adjusted descending start.","Signed bounds and fixed negative stride.",
        ("int i=first","int i=0"))
    add("post-loop-only-origin",
        "int f(int a,int b){int first=a+9;int sum=1;for(int i=1;i<b;i++){sum+=i;}return sum+first;}",
        [(0,2),(5,4),(-2,10),(3,0),(4,6),(-8,3)],
        lambda a,b:a+10+sum(range(1,b)),"Use a one-based range and add a separate calibration.",
        "Signed calibration and nonnegative bound.",("int i=1","int i=2"))
    add("projection-limit-control",
        "int f(int n,int bias){int result=bias;for(int i=0;i<n;i++){result+=2;}return result;}",
        [(67,3),(75,-1),(0,6),(2,1),(99,8),(4,-1)],lambda n,b:2*n+b,
        "Use a deliberate range exceeding the projection budget on some inputs.",
        "Small signed bias and counts 0–99.")
    add("side-effect-domain-control",
        "int trials=0;int f(int n){trials++;if(n<0){return trials-8;}return n*3+trials;}",
        [(-2,),(-1,),(0,),(2,),(-9,),(13,)],lambda n:-7 if n<0 else n*3+1,
        "Preserve the global counter update ahead of a deliberate sentinel.",
        "Each verification vector starts with fresh globals.")
    add("array-extent-negative",
        "int f(int i,int x){int slab[2];slab[0]=x;slab[1]=x+9;return slab[i];}",
        [(1,1),(0,3),(1,4),(0,-2),(1,7),(0,11)],lambda i,x:x+9*i,
        "Return the specified physical cell within a fixed extent.","Indices zero and one.",
        ("slab[i]","slab[i+1]"))
    add("incomplete-domain-samples","int f(int q,int n){if(q<0){return 8;}return n+1;}",
        [(1,2),(5,-3),(12,4)],lambda q,n:n+1,
        "Only nonnegative positions are sampled.","Negative positions unspecified.",holdout=0)
    return rows


def freeze():
    rows=fixtures()
    payload=(json.dumps(rows,indent=2,ensure_ascii=False)+"\n").encode()
    hashes={item.name:sha256(item.read_bytes()).hexdigest() for item in sorted((ROOT/"upstream").iterdir())
            if not item.name.startswith(".")}
    (ROOT/"cases-v1.json").write_bytes(payload)
    (ROOT/"manifest-v1.json").write_text(json.dumps(dict(
        revision="multiple pinned upstream revisions",case_sha256=sha256(payload).hexdigest(),
        upstream_sha256=hashes,partitions=dict(Counter(row["partition"] for row in rows)),
        external_sources={key:list(value) for key,value in EXTERNAL.items()},
        grouping="One split per upstream repository and algorithm family. Archived Phase 9 adaptations are diagnostics only.",
        holdout="Generate with supplied discovery only, then submit candidates separately to the isolated worker."
    ),indent=2)+"\n")


if __name__=="__main__":
    freeze()
