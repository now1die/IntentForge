"""Replay each pinned revision independently of the application."""
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
from .phase105_audit import audit
from .phase105_fixtures import EXTERNAL, JAVA, JS, ROOT

UPSTREAM = ROOT/"upstream"


def python(path,revision,arguments):
    target = path/"source.py"
    copyfile(UPSTREAM/f"leftmost-{revision}.py",target)
    script = path/"replay.py"
    script.write_text("import json\nfrom source import binary_search\n"
                      f"print(json.dumps([binary_search(row[1:],row[0]) for row in {arguments!r}]))\n")
    return json.loads(command([sys.executable,str(script)],path))


def javascript(path,revision,arguments):
    source = (UPSTREAM/f"coprime-{revision}.js").read_text()
    # Resolve the archived extensionless import as a standalone ESM module.
    (path/"source.mjs").write_text(source.replace("'./GetEuclidGCD'","'./GetEuclidGCD.mjs'"))
    copyfile(UPSTREAM/"GetEuclidGCD.js",path/"GetEuclidGCD.mjs")
    script = path/"replay.mjs"
    script.write_text("import { CoPrimeCheck } from './source.mjs';\n"+
                      "console.log(JSON.stringify("+json.dumps(arguments)+".map(row => CoPrimeCheck(...row))));\n")
    return json.loads(command(["node",str(script)],path))


def java(path,revision,arguments):
    copyfile(UPSTREAM/f"interpolation-{revision}.java",path/"InterpolationSearch.java")
    example = "{"+",".join("{"+",".join(map(str,row))+"}" for row in arguments)+"}"
    (path/"Harness.java").write_text(f"""package com.thealgorithms.searches;
import java.util.Arrays;
public class Harness {{
    public static void main(String[] args) {{
        int[][] inputs = {example};
        for (int[] row : inputs) {{
            try {{
                System.out.println(new InterpolationSearch().find(Arrays.copyOfRange(row,1,row.length),row[0]));
            }} catch (ArithmeticException ex) {{
                System.out.println("DIVISION_BY_ZERO");
            }} catch (IndexOutOfBoundsException ex) {{
                System.out.println("ARRAY_BOUNDS");
            }}
        }}
    }}
}}
""")
    jar = os.getenv("PHASE105_ECJ_JAR")
    if jar:
        compiler = ["java","-jar",str(Path(jar).resolve()),"-17","-proc:none"]
    elif which("javac"):
        compiler = ["javac","-proc:none"]
    else:
        raise RuntimeError("Install javac or set PHASE105_ECJ_JAR.")
    classes = path/"classes"
    classes.mkdir()
    command([*compiler,"-d",str(classes),"InterpolationSearch.java","Harness.java"],path)
    lines = command(["java","-cp",str(classes),"com.thealgorithms.searches.Harness"],path)
    return [int(line) if line.lstrip("-").isdigit() else line for line in lines.splitlines()]


def replay(cases):
    oracle = MiniCOracle()
    result = {}
    for row in cases:
        if row["fault_origin"]!="adapted-real-defect":
            continue
        repository = EXTERNAL[row["family"]][0]
        runner = {JAVA:java,JS:javascript}.get(repository,python)
        discovery = row["vectors"]
        tests = discovery+row["holdout_vectors"]
        outcomes = {}
        for revision,code in (("before",row["source"]),("after",row["references"][0])):
            with TemporaryDirectory(prefix="p105-upstream-") as work:
                originals = runner(Path(work),revision,[test["arguments"] for test in tests])
            translated = []
            for test in tests:
                outcome=oracle.verify(code,"f",(Vector.model_validate(test),),ExecutionLimits())
                issue=outcome.execution.issue
                translated.append(issue.code if issue else outcome.observations[0].actual)
            assert originals==translated,(row["id"],revision,originals,translated)
            outcomes[revision] = [{"input":test["arguments"],"expected":test["expected"],"upstream":original,
                                  "mini_c":adapted,"partition":"discovery" if i<len(discovery) else "holdout"}
                                 for i,(test,original,adapted) in enumerate(zip(tests,originals,translated,strict=True))]
        assert any(row["upstream"]!=row["expected"] for row in outcomes["before"][:len(discovery)])
        assert all(row["upstream"]==row["expected"] for row in outcomes["after"])
        result[row["family"]]=outcomes
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write",action="store_true")
    args=parser.parse_args()
    result = replay(audit()[0])
    if args.write:
        (REPORTS/"phase105-upstream-v1.json").write_text(json.dumps(result,indent=2)+"\n")
    print(f"Replayed {len(result)} pinned defect pairs on {sum(len(pair['after']) for pair in result.values())} distinct family inputs")
