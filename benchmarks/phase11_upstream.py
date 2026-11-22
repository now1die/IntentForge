"""Replay pinned numeric domains in Python, Node and Java outside the API."""
import argparse
import json
import os
from pathlib import Path
from shutil import copyfile, which
import sys
from tempfile import TemporaryDirectory

from ai.behavior_oracle import ExecutionLimits, Vector
from vm.behavioral_executor import MiniCOracle

from .phase6_evaluate import REPORTS
from .phase95_upstream import command
from .phase11_audit import audit
from .phase11_fixtures import EXTERNAL, JAVA, JS, ROOT

UPSTREAM=ROOT/"upstream"


def python(path,revision,inputs):
    copyfile(UPSTREAM/f"exponential-{revision}.py",path/"source.py")
    harness=path/"harness.py"
    harness.write_text(f"""import json
from source import exponential_search
results = []
for row in {inputs!r}:
    try:
        results.append(exponential_search(row[1:],row[0]))
    except RecursionError:
        results.append("CALL_DEPTH")
print(json.dumps(results))
""")
    return json.loads(command([sys.executable,str(harness)],path))


def javascript(path,revision,inputs):
    copyfile(UPSTREAM/f"mean-{revision}.js",path/"source.mjs")
    harness=path/"harness.mjs"
    harness.write_text("""import { mean } from './source.mjs';
const rows = """+json.dumps(inputs)+""";
const results = rows.map(([length,...values]) => {
    try {
        const result = mean(values.slice(0,length));
        return Number.isNaN(result) ? "DIVISION_BY_ZERO" : result;
    } catch (issue) {
        if (issue.message !== "Array is empty") throw issue;
        return -912;
    }
});
console.log(JSON.stringify(results));
""")
    return json.loads(command(["node",str(harness)],path))


def java(path,revision,inputs):
    copyfile(UPSTREAM/f"row-{revision}.java",path/"BinarySearch2dArray.java")
    samples="{"+",".join("{"+",".join(map(str,row))+"}" for row in inputs)+"}"
    (path/"Harness.java").write_text(f"""package com.thealgorithms.searches;
import java.util.Arrays;
public class Harness {{
    public static void main(String[] args) {{
        int[][] cases={samples};
        for (int[] row: cases) {{
            try {{
                System.out.println(BinarySearch2dArray.binarySearch(
                    new int[][]{{Arrays.copyOfRange(row,1,row.length)}},row[0])[1]);
            }} catch (IndexOutOfBoundsException issue) {{
                System.out.println("ARRAY_BOUNDS");
            }}
        }}
    }}
}}
""")
    jar=os.getenv("PHASE11_ECJ_JAR")
    if jar:
        compiler=["java","-jar",str(Path(jar).resolve()),"-17","-proc:none"]
    elif which("javac"):
        compiler=["javac","-proc:none"]
    else:
        raise RuntimeError("Install javac or set PHASE11_ECJ_JAR.")
    classes=path/"classes"
    classes.mkdir()
    command([*compiler,"-d",str(classes),"BinarySearch2dArray.java","Harness.java"],path)
    values=command(["java","-cp",str(classes),"com.thealgorithms.searches.Harness"],path).splitlines()
    return [int(line) if line.lstrip("-").isdigit() else line for line in values]


def replay(cases):
    vm=MiniCOracle()
    report={}
    for case in cases:
        if case["fault_origin"]!="adapted-real-defect":
            continue
        runner={JAVA:java,JS:javascript}.get(EXTERNAL[case["family"]][0],python)
        discovery=case["vectors"]
        all_vectors=discovery+case["holdout_vectors"]
        observed={}
        for label,code in (("before",case["source"]),("after",case["references"][0])):
            with TemporaryDirectory(prefix="phase11-upstream-") as directory:
                values=runner(Path(directory),label,[row["arguments"] for row in all_vectors])
            adapted=[]
            for row in all_vectors:
                result=vm.verify(code,"f",(Vector.model_validate(row),),ExecutionLimits())
                issue=result.execution.issue
                adapted.append(issue.code if issue else result.observations[0].actual)
            assert adapted==values,(case["id"],label,adapted,values)
            observed[label]=[dict(input=row["arguments"],expected=row["expected"],upstream=original,mini_c=translated,
                                  partition="discovery" if i<len(discovery) else "holdout")
                             for i,(row,original,translated) in enumerate(zip(all_vectors,values,adapted,strict=True))]
        assert any(row["upstream"]!=row["expected"] for row in observed["before"][:len(discovery)])
        assert all(row["upstream"]==row["expected"] for row in observed["after"])
        report[case["family"]]=observed
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write",action="store_true")
    args=parser.parse_args()
    report=replay(audit()[0])
    if args.write:
        (REPORTS/"phase11-upstream-v1.json").write_text(json.dumps(report,indent=2)+"\n")
    print(f"Replayed {len(report)} pinned defect pairs on {sum(len(pair['after']) for pair in report.values())} family inputs")
