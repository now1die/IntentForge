"""Freeze small independent documented adaptations and authored controls."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).with_name("phase12_data")
EXTERNAL = {
    "jump-empty-input": {
        "repository": "TheAlgorithms/Python", "path": "searches/jump_search.py",
        "before": "481dd54e975c4a3c2eb37465fc40ad484c53ed85",
        "after": "13f71409f675eec1c59aef6ff2bac9d3b2a74617", "archive": "jump", "license": "MIT",
        "adaptation": "Sorted distinct int prefixes of length 0–4. Replace floor sqrt with the equivalent three-way constant rule. Empty IndexError maps to ARRAY_BOUNDS.",
    },
    "cycle-sort-return-kind": {
        "repository": "TheAlgorithms/JavaScript", "path": "Sorts/CycleSort.js",
        "before": "b3e6eed3cef3d82b5bb4989c0a2406698e847832",
        "after": "0da3880955e0641b4d6b34782bd3892cb4b08802", "archive": "cycle", "license": "GPL-3.0",
        "adaptation": "Four distinct signed integer cells. Broken numeric write count is preserved. Correct returned array is projected to its first element.",
    },
}

JUMP = """int smaller(int left,int right){if(left<right){return left;}return right;}
int f(int n,int key,int a,int b,int c,int d){
 int cells[4];cells[0]=a;cells[1]=b;cells[2]=c;cells[3]=d;
 int stride=1;if(n==0){stride=0;}if(n==4){stride=2;}
 int previous=0;int step=stride;
 while(cells[smaller(step,n)-1]<key){previous=step;step+=stride;if(previous>=n){return -1;}}
 while(cells[previous]<key){previous++;if(previous==smaller(step,n)){return -1;}}
 if(cells[previous]==key){return previous;}return -1;
}"""
JUMP_FIXED = JUMP.replace(" int stride=1;", " if(n==0){return -1;}int stride=1;")
CYCLE = """int f(int u,int v,int w,int z){
 int list[4];list[0]=u;list[1]=v;list[2]=w;list[3]=z;int writes=0;
 for(int first=0;first<4;first++){
   int value=list[first];int pos=first;
   for(int i=first+1;i<4;i++){if(list[i]<value){pos++;}}
   if(pos==first){continue;}
   while(value==list[pos]){pos++;}
   int old=list[pos];list[pos]=value;value=old;writes++;
   while(pos!=first){
     pos=first;
     for(int j=first+1;j<4;j++){if(list[j]<value){pos++;}}
     while(value==list[pos]){pos++;}
     int next=list[pos];list[pos]=value;value=next;writes++;
   }
 }
 return writes;
}"""
CYCLE_FIXED = CYCLE.replace("return writes;", "return list[0];")
PRESENCE = """int f(bool use,int value,int base){
 int member=-7;bool found=false;
 if(use){member=value;found=true;}
 if(member==-7){return base;}return member;
}"""
PRESENCE_FIXED = PRESENCE.replace("member==-7", "!found")
GRID = """int f(int band,int slot,int head,int tail){
 int map[6];map[0]=head;map[1]=17;map[2]=0;map[3]=32;map[4]=-1;map[5]=tail;
 if(slot<0 || slot>=3){return -19;}return map[band*3+slot];
}"""
GRID_FIXED = GRID.replace("slot>=3", "slot>=3 || band < 0 || band >= 2")
PREFIX = """int f(int count,int a,int b,int c,int d,int e){
 int data[5];data[0]=a;data[1]=b;data[2]=c;data[3]=d;data[4]=e;
 if(count==0){return data[0];}int value=0;
 for(int j=0;j<count;j++){if(data[j]<0){value++;}}return value;
}"""
PREFIX_FIXED = PREFIX.replace("return data[0];", "return 0;")


def search(n, key, *cells):
    values = cells[:n]
    return values.index(key) if key in values else -1


def fixtures():
    rows = []

    def add(family, broken, fixed, inputs, expected, description, *, partition="final", both=True):
        vectors = [{"arguments": list(args), "expected": expected(*args)} for args in inputs]
        assert len({tuple(vector["arguments"]) for vector in vectors}) == len(vectors)
        provenance = {"group": "authored", "origin": "IntentForge Phase 12"}
        if family in EXTERNAL:
            external = EXTERNAL[family]
            provenance = external | {"group": "adapted_real_defect",
                                     "origin": f"https://github.com/{external['repository']}/commit/{external['after']}"}
        shared = {"family": family, "partition": partition, "compiler_valid": True, "requirement": None,
                  "specification": description, "domain": description, "vectors": vectors[:-3],
                  "holdout_vectors": vectors[-3:], "provenance": provenance}
        if both:
            rows.append(shared | {"id": family + "-fault", "source": broken, "references": [fixed],
                                  "disposition": "fault", "fault_origin": "adapted-real-defect"
                                  if family in EXTERNAL else "authored-injected"})
        rows.append(shared | {"id": family + "-control", "source": fixed, "references": [],
                              "disposition": "control", "fault_origin": None})

    add("jump-empty-input", JUMP, JUMP_FIXED,
        [(0, 19, 24, 73, 20, 18), (4, 20, 0, 7, 10, 20), (2, -9, -9, 6, 88, 96),
         (4, 6, -4, 0, 7, 12), (1, -20, 3, 10, 6, 4), (0, -31, -8, 4, 92, -29),
         (3, 71, -1, 41, 71, -82), (4, 17, -1, 0, 8, 11)], search,
        "Jump search over sorted distinct active prefixes of four physical cells.")
    add("cycle-sort-return-kind", CYCLE, CYCLE_FIXED,
        [(8, 3, -4, 19), (5, 2, 9, 6), (-31, 1, -3, 4), (9, 8, 7, 6), (5, -28, 31, 0),
         (23, 65, 28, 77), (-29, -70, -32, -48), (1, 2, 3, 4)], lambda *values: min(values),
        "Cycle sort over distinct values, observed through the first returned element.")
    add("optional-value-write", PRESENCE, PRESENCE_FIXED,
        [(True, -7, 43), (False, 6, 44), (True, 0, -22), (True, -33, -33), (False, -7, 52),
         (True, -7, -40), (False, -7, -7), (True, 19, 8)], lambda use, value, base: value if use else base,
        "An explicit optional write can store any signed value.")
    add("rectangular-row-alias", GRID, GRID_FIXED,
        [(-1, 2, 82, 67), (2, 0, 48, 91), (0, 0, 13, -5), (1, 2, 79, 56), (0, -1, 49, 11),
         (-1, 0, 23, 34), (41, 1, 83, 29), (1, 1, 27, 13)],
        lambda row, col, a, b: [a, 17, 0, 32, -1, b][row * 3 + col] if 0 <= row < 2 and 0 <= col < 3 else -19,
        "Independent signed coordinates select a cell of a rectangular grid.")
    add("empty-negative-count", PREFIX, PREFIX_FIXED,
        [(0, -8, 61, -53, 21, -1), (3, -1, 0, 2, -6, -7), (5, -2, -3, -61, 10, 0),
         (1, 0, -10, -21, -9, -4), (2, -16, -2, -22, 31, 5), (0, 57, 2, 3, -19, -2),
         (4, -1, -2, -9, 0, -64), (5, 4, 7, 8, 23, 45)],
        lambda n, *cells: sum(value < 0 for value in cells[:n]),
        "Count negative entries in an active prefix that may be empty.")
    add("conditional-boolean-return", "", "bool f(bool a,bool b,bool c){if(a&&b){return c;}return a||c;}",
        [(True, False, False), (True, True, False), (True, True, True), (False, True, True),
         (False, False, False), (False, False, True)], lambda a, b, c: c if a and b else a or c,
        "Inert Boolean selection control.", partition="development", both=False)
    add("paired-integer-order", "", "int f(int a,int b,int c){int x=c;if(a<b){x=b-a;}return x;}",
        [(7, 18, 8), (-4, 0, -1), (12, -4, 7), (0, 10, -2), (-19, -2, 8), (7, 7, 36)],
        lambda a, b, c: b-a if a<b else c, "Selection control for a conditional arithmetic result.",
        partition="selection", both=False)
    return rows


def freeze():
    payload = (json.dumps(fixtures(), indent=2) + "\n").encode()
    (ROOT / "cases-v1.json").write_bytes(payload)
    manifest = {"version": 1, "case_sha256": sha256(payload).hexdigest(),
                "partitions": dict(Counter(row["partition"] for row in fixtures())),
                "external_sources": EXTERNAL,
                "upstream_sha256": {path.name: sha256(path.read_bytes()).hexdigest()
                                    for path in sorted((ROOT / "upstream").iterdir())}}
    (ROOT / "manifest-v1.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    freeze()
