"""Replay pinned upstream functions and compare faithful Mini-C translations.

Node and a Java compiler are only needed for this provenance replay. They are
not application dependencies, and no evaluator is added to the public API.
"""
import json
import os
from pathlib import Path
from shutil import copyfile, which
from subprocess import run
from tempfile import TemporaryDirectory

from ai.behavior_oracle import ExecutionLimits, Vector
from vm.behavioral_executor import MiniCOracle

from .phase6_evaluate import REPORTS
from .phase95_audit import audit
from .phase95_fixtures import ROOT, JAVA, EXTERNAL

UPSTREAM = ROOT/"upstream"


def command(args, path):
    return run(args,cwd=path,text=True,capture_output=True,timeout=30,check=True).stdout


def javascript(path, archive, revision, arguments):
    original = (UPSTREAM/f"{archive}-{revision}.js").read_text()
    if archive=="multiples":
        # Instantiate exactly the numeric declaration, excluding read/print.
        start = "function multiplesThreeAndFive" if revision=="before" else "const multiplesThreeAndFive"
        end = "\nvar num" if revision=="before" else "\nconst rl"
        logic = original[original.index(start):original.index(end)]
        tail = "const values = args.map(row => multiplesThreeAndFive(...row));"
    else:
        logic = original
        tail = """const values = args.map(row => DateDayDifference(
            row.slice(0,3).join('/'), row.slice(3,6).join('/')));"""
    harness = path/"harness.mjs"
    harness.write_text(logic+"\nconst args="+json.dumps(arguments)+";\n"+tail+
                       "\nconsole.log(JSON.stringify(values));\n")
    return json.loads(command(["node",str(harness)],path))


def java(path, archive, revision, arguments):
    if archive=="smith":
        source, call = "SmithNumber", "SmithNumber.isSmithNumber(row[0])"
        extras = {"PrimeCheck.java":"PrimeCheck.java","SumOfDigits.java":"SumOfDigits.java"}
    elif archive=="binary":
        source, call = "BinarySearch", "new BinarySearch().find(cells,row[0])"
        extras = {"BinarySearchAlgorithm.java":"SearchAlgorithm.java"}
    else:
        source, call = "ExponentialSearch", "new ExponentialSearch().find(cells,row[0])"
        extras = {"ExponentialSearchAlgorithm.java":"SearchAlgorithm.java"}
    sources = [f"{source}.java","Harness.java",*extras.values()]
    copyfile(UPSTREAM/f"{archive}-{revision}.java",path/f"{source}.java")
    for archived,expected in extras.items():
        copyfile(UPSTREAM/archived,path/expected)
    examples = "{"+",".join("{"+",".join(map(str,inputs))+"}" for inputs in arguments)+"}"
    (path/"Harness.java").write_text(f"""package com.thealgorithms.searches;
import java.util.Arrays;
{'import com.thealgorithms.maths.SmithNumber;' if archive=='smith' else ''}
public class Harness {{
    public static void main(String[] args) {{
        int[][] rows = {examples};
        for (int[] row : rows) {{
            Integer[] cells = Arrays.stream(row).skip(1).boxed().toArray(Integer[]::new);
            try {{ System.out.println({call}); }}
            catch (ArrayIndexOutOfBoundsException err) {{ System.out.println("ARRAY_BOUNDS"); }}
        }}
    }}
}}
""")
    jar = os.getenv("PHASE95_ECJ_JAR")
    if jar:
        javac = ["java","-jar",str(Path(jar).resolve()),"-17","-proc:none"]
    elif which("javac"):
        javac = ["javac","-proc:none"]
    else:
        raise RuntimeError("Set PHASE95_ECJ_JAR or use an installed javac")
    out = path/"classes"
    out.mkdir()
    command([*javac,"-d",str(out),*sources],path)
    lines = command(["java","-cp",str(out),"com.thealgorithms.searches.Harness"],path)
    return ["ARRAY_BOUNDS" if line=="ARRAY_BOUNDS" else json.loads(line) for line in lines.splitlines()]


def replay(cases):
    oracle = MiniCOracle()
    outputs = {}
    for row in cases:
        if row["fault_origin"]!="adapted-real-defect":
            continue
        repo,_,archive,*_ = EXTERNAL[row["family"]]
        tests = row["vectors"]+row["holdout_vectors"]
        args = [vector["arguments"] for vector in tests]
        outcomes = {}
        for revision,code in (("before",row["source"]),("after",row["references"][0])):
            with TemporaryDirectory(prefix="p95-upstream-") as workspace:
                runner = java if repo==JAVA else javascript
                upstream = runner(Path(workspace),archive,revision,args)
            modeled = []
            for test in tests:
                result = oracle.verify(code,"f",(Vector.model_validate(test),),ExecutionLimits())
                issue = result.execution.issue
                modeled.append(issue.code if issue else result.observations[0].actual)
            assert upstream==modeled,(row["id"],revision,upstream,modeled)
            outcomes[revision] = [{"input":vector["arguments"],"expected":vector["expected"],"upstream":original,
                                    "adapted":translation}
                                   for vector,original,translation in zip(tests,upstream,modeled,strict=True)]
        assert any(item["upstream"]!=item["expected"] for item in outcomes["before"])
        assert all(item["upstream"]==item["expected"] for item in outcomes["after"])
        outputs[row["family"]] = outcomes
    return outputs


if __name__=="__main__":
    cohort,_ = audit()
    result = replay(cohort)
    (REPORTS/"phase95-upstream-v1.json").write_text(json.dumps(result,indent=2)+"\n")
    print("Verified exact upstream-to-adaptation outcomes on "+str(sum(len(v["after"]) for v in result.values()))+" inputs")
