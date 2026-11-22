"""Frozen Phase 11.5 documented specimens and authored controls."""
from collections import Counter
from hashlib import sha256
from itertools import combinations
import json
from math import prod
from pathlib import Path

ROOT = Path(__file__).with_name("phase115_data")
PYTHON, JS, JAVA = ("TheAlgorithms/"+language for language in ("Python","JavaScript","Java"))
EXTERNAL = {
    "empty-retained-run":(PYTHON,"sorts/stalin_sort.py","retained",
        "4d9d79f797d1f8eb97d31d4a6813e829cfa693d2","5386e4900b83a7f26a46507f20a46b6c9bf25f77",
        "MIT","Project the retained list to its sum on a fixed physical array with a variable logical prefix. Empty IndexError maps to ARRAY_BOUNDS."),
    "negative-product-placeholder":(JS,"Dynamic-Programming/MaxProductOfThree.js","product",
        "5ce828b3fe4e138c6da652bf03870e2c20e2f692","6aa3314b93d1556e5dac4be2017a60a2f35bad64",
        "GPL-3.0","Keep the five-cell traversal and compare slots. Use -99 to encode the fixed null state, outside the signed input domain."),
    "saddleback-negative-column":(JAVA,"src/main/java/com/thealgorithms/searches/SaddlebackSearch.java","saddle",
        "402d3b056554cbb973c488941df0307b257bdc1b","401e25388def688d457ccab49dd84dd97d9d1b49",
        "MIT","Keep the explicit starting row and column on a single ordered row. Return the result column and normalize native index errors."),
}

CELLS4="int lane[4];lane[0]=a;lane[1]=b;lane[2]=c;lane[3]=d;"
CELLS5="int data[5];data[0]=a;data[1]=b;data[2]=c;data[3]=d;data[4]=e;"

PREFIX = "int f(int n,int a,int b,int c,int d,int e){"+CELLS5+"""
    if(n==0){return -31;}int p=0;int q=n-1;
    while(p<q){int center=p+(q-p)/2;
       if(data[center]>data[q]){p=center+1;}
       else if(data[center]==data[q]){q--;}else{q=center;}}
    return p;}"""
PREFIX_FIXED=PREFIX.replace("return p;}","if(p>0 && data[p]==data[0]){return 0;}return p;}")
PREFIX_INPUTS=[(0,19,4,18,2,6),(1,8,-16,3,1,2),(2,5,5,-15,1,2),(4,1,4,6,1,-25),(5,-2,0,4,9,-2),
               (3,6,-5,-5,-18,10),(5,0,0,0,0,0),(3,1,7,1,-20,0),(5,4,6,7,1,3)]

DIGITS="""int fold(int key,int tag){int out=0;int place=1;while(key>0||tag>0){
    if(key%2!=tag%2){out+=place;}key=key/2;tag=tag/2;place*=2;}return out;}"""
SHIFT = DIGITS+"int f(int a,int b,int c,int d){"+CELLS4+"""
    int base=a;int ceiling=a;
    for(int i=1;i<4;i++){if(lane[i]<base){base=lane[i];}if(lane[i]>ceiling){ceiling=lane[i];}}
    int checksum=ceiling;
    for(int k=base;k<base+4;k++){checksum=fold(checksum,fold(lane[k-base],k+2));}
    return checksum;}"""
SHIFT_FAULT=SHIFT.replace("int checksum=ceiling","int checksum=2").replace("int k=base","int k=0")

ENDPOINT="""int position(int bottom,int top,int a,int b,int c,int d,int match){"""+CELLS4+"""
    if(top<bottom){return -29;}int place=(top+bottom)/2;
    if(match<lane[place]){return position(bottom,place-1,a,b,c,d,match);}
    if(match>lane[place]){return position(place+1,top,a,b,c,d,match);}
    return place;}
    int f(int a,int b,int c,int d,int match){return position(0,3,a,b,c,d,match);}"""
ENDPOINT_FAULT=ENDPOINT.replace("    if(top<bottom)", "    if(0>top){top=3;}if(top<bottom)")


def retained_sum(n,*cells):
    if not n:
        return 0
    total=last=cells[0]
    for value in cells[1:n]:
        if value>=last:
            total+=value
            last=value
    return total


def shifted_sum(*cells):
    value=max(cells)
    for index,cell in enumerate(cells,min(cells)+2):
        value ^= index ^ cell
    return value


def first_min(n,*cells):
    return cells.index(min(cells[:n])) if n else -31


def find(a,b,c,d,key):
    cells=(a,b,c,d)
    return cells.index(key) if key in cells else -29


def fixtures():
    rows=[]

    def add(family,code,inputs,reference,description,domain,*,fault=None,partition="final",holdout=2):
        vectors=[{"arguments":list(args),"expected":reference(*args)} for args in inputs]
        assert len({tuple(row["arguments"]) for row in vectors})==len(vectors)
        assert 3<=len(vectors)-holdout<=12
        provenance=dict(group="authored",origin="IntentForge Phase 11.5",license="repository license")
        if family in EXTERNAL:
            repo,path,archive,before,after,license_name,adaptation=EXTERNAL[family]
            provenance=dict(group="adapted_real_defect",origin=f"https://github.com/{repo}/commit/{after}",
                            repository=repo,path=path,archive=archive,before=before,after=after,
                            license=license_name,adaptation=adaptation)
        provenance["review"]="Independent executable expected outputs. Human review unavailable."
        common=dict(family=family,partition=partition,compiler_valid=True,requirement=None,specification=description,
                    domain=domain,vectors=vectors[:-holdout],holdout_vectors=vectors[-holdout:],provenance=provenance)
        if fault is not None:
            rows.append(dict(common,id=family+"-fault",source=fault,references=[code],disposition="fault",
                             fault_origin="adapted-real-defect" if family in EXTERNAL else "project-injected"))
        rows.append(dict(common,id=family+"-control",source=code,references=[],disposition="control",fault_origin=None))

    development="int f(int rise,int fall){int n=3*rise-fall;if(n>4){return 10;}return n-6;}"
    add("development-switchpoint",development,[(2,1),(2,2),(-1,5),(4,1),(8,3),(1,-2)],
        lambda a,b:10 if 3*a-b>4 else 3*a-b-6,"Check the exclusive signed switching point.",
        "Small signed values.",fault=development.replace("n>4","n>=4"),partition="development")
    selection="int f(int steps){int point=4;for(int j=3;j<steps;j+=2){point+=2*j+5;}return point;}"
    add("selection-odd-points",selection,[(3,),(5,),(7,),(9,),(11,),(2,)],
        lambda n:4+sum(2*j+5 for j in range(3,n,2)),"Sum odd points below the boundary.",
        "Small nonnegative bounds.",fault=selection.replace("j<steps","j<=steps"),partition="selection")

    retained="int f(int n,int a,int b,int c,int d){"+CELLS4+"""
        if(n==0){return 0;}int last=lane[0];int total=last;
        for(int j=1;j<n;j++){if(lane[j]>=last){last=lane[j];total+=last;}}return total;}"""
    add("empty-retained-run",retained,[(0,0,0,0,0),(4,10,5,9,2),(3,-4,-4,9,20),(1,-10,4,7,8),(2,4,3,1,2),
        (0,10,9,3,5),(4,2,3,0,4),(4,9,8,7,6)],retained_sum,
        "Sum the retained nondecreasing run and use a neutral value for the empty input.",
        "Four signed physical cells, zero through four logical cells.",
        fault=retained.replace("if(n==0){return 0;}","if(n==0){return lane[n-1];}"),holdout=3)

    product="int f(int a,int b,int c,int d,int e){"+CELLS5+"""
        int x=data[0];int y=UNSET;int z=UNSET;int p=data[0];int q=UNSET;
        for(int j=1;j<5;j++){
           if(data[j]>x){z=y;y=x;x=data[j];}
           else if(y==UNSET||data[j]>y){z=y;y=data[j];}
           else if(z==UNSET||data[j]>z){z=data[j];}
           if(data[j]<p){q=p;p=data[j];}
           else if(q==UNSET||data[j]<q){q=data[j];}}
        int left=x*y*z;int right=x*p*q;if(left>right){return left;}return right;}"""
    add("negative-product-placeholder",product.replace("UNSET","-99"),
        [(-1,-1,-1,-2,-2),(-2,-1,-2,-3,-3),(1,2,3,0,-1),(-3,-2,-1,-2,-1),(-1,-3,-2,-1,-1),
         (-1,-3,-1,-2,-5),(-2,-1,-3,-1,-5),(1,-1,-1,-2,-3)],
        lambda *items:max(prod(group) for group in combinations(items,3)),
        "Return the largest signed product of a distinct-position triple.",
        "Five small signed cells, with -1 used as ordinary data.",fault=product.replace("UNSET","-1"),holdout=3)

    saddle="""int march(int row,int col,int target,int a,int b,int c,int d){"""+CELLS4+"""
        if(row<0 || col>=4 SAFETY){return -1;}if(row>=1){return lane[4];}
        if(lane[col]==target){return col;}if(lane[col]>target){return march(row-1,col,target,a,b,c,d);}
        return march(row,col+1,target,a,b,c,d);}
        int f(int row,int col,int target,int a,int b,int c,int d){return march(row,col,target,a,b,c,d);}"""
    add("saddleback-negative-column",saddle.replace(" SAFETY"," || row>=1 || col<0"),
        [(0,-1,5,-1,2,5,7),(1,0,6,0,2,4,6),(0,1,5,-1,2,5,7),(0,0,-3,-1,2,5,7),(-1,1,3,1,2,3,5),
         (0,-3,1,-1,1,4,7),(0,4,9,1,3,7,9),(0,0,9,1,3,7,9)],
        lambda r,c,k,*cells:cells.index(k) if r==0 and 0<=c<4 and k in cells[c:] else -1,
        "Return the matching column or a sentinel from the explicitly supplied start.",
        "A single ordered row and in-range or invalid explicit starting coordinates.",
        fault=saddle.replace(" SAFETY",""),holdout=3)

    add("first-minimum-on-logical-seam",PREFIX_FIXED,PREFIX_INPUTS,first_min,
        "Return the first minimum in the cyclically ordered prefix, with a distinct empty result.",
        "Physical extent five and logical size zero through five. Inactive cells can be smaller.",
        fault=PREFIX,holdout=2)
    add("reaching-maximum-seed",SHIFT,[(0,2,17,19),(5,6,9,5),(4,12,17,18),(9,12,15,17),
        (5,5,11,20),(1,7,20,12),(10,2,6,8)],shifted_sum,
        "XOR an observed maximum seed, every observed cell, and the four integer coordinates above the observed minimum.",
        "Four nonnegative cells. Duplicates and gaps are valid.",fault=SHIFT_FAULT)
    add("explicit-upper-argument",ENDPOINT,[(5,7,9,13,0),(5,7,9,13,5),(5,7,9,13,13),(5,7,9,13,8),
        (-9,-7,-3,-2,-21),(-9,-7,-3,-2,-7),(8,14,19,26,7)],
        find,"Use the passed inclusive bound and a separate no-match value.",
        "Four distinct increasing signed values.",fault=ENDPOINT_FAULT)
    add("negative-coordinate-control","int f(int p,int n){if(n==0){return -37;}return p-n*2;}",
        [(-4,2),(0,0),(7,6),(15,2),(-1,0),(-3,7)],
        lambda p,n:-37 if n==0 else p-n*2,"Distinguish a negative coordinate from an empty-result sentinel.",
        "Signed coordinates and nonnegative lengths.")
    add("endpoint-zero-control","int f(int key,int a,int b,int c,int d){"+CELLS4+
        "int cursor=0;for(int j=0;j<4;j++){if(lane[j]<key){cursor++;}}return cursor;}",
        [(0,1,2,2,4),(3,1,2,2,4),(7,1,2,2,4),(2,2,2,2,2),(4,3,3,5,7),(-1,-2,-2,4,8)],
        lambda k,*cells:sum(x<k for x in cells),"Return the lower insertion position including zero and extent.",
        "Four nondecreasing signed cells.")
    add("logical-three-cell-control",PREFIX_FIXED,
        [(3,1,4,1,-6,-9),(3,2,8,-5,-6,-9),(2,-2,-2,-4,-7,-8),(0,17,1,-9,2,3),
         (1,-4,-8,-12,-15,-19),(3,6,8,9,-4,-8)],first_min,
        "Find a minimum in logical prefixes up to three cells.",
        "Cyclic signed logical prefixes and independently varied inactive cells.")
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
        holdout="Fresh restricted-worker verification with comparison disabled.",
        grouping="Each project and algorithm family is confined to one partition."),indent=2)+"\n")


if __name__=="__main__":
    freeze()
