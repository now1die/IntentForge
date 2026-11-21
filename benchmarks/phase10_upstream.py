"""Replay unmodified pinned Python and Java logic before and after each fix."""
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
from .phase10_audit import audit
from .phase10_fixtures import EXTERNAL, JAVA, ROOT

UPSTREAM = ROOT/"upstream"


def definition(source, name):
    start = source.index(f'def {name}(')
    end = source.index('\ndef ', start)
    return source[start:end].rstrip()


def python(path, archive, revision, arguments):
    source = (UPSTREAM/f"{archive}-{revision}.py").read_text()
    if archive=="recursion":
        # The surrounding old Python module has Python 2 CLI syntax.
        start = source.index("def binary_search_by_recursion(")
        end = source.index("\ndef __assert_sorted(",start)
        logic = source[start:end]
        call = "binary_search_by_recursion(row[1:], row[0], 0, len(row)-2)"
    else:
        gcd = (UPSTREAM/"gcd.py").read_text()
        logic = definition(gcd,"greatest_common_divisor")+"\n\n"+definition(source,"least_common_multiple_fast")
        call = "least_common_multiple_fast(*row)"
    script = path/"harness.py"
    script.write_text(logic+f"""
import json
observations = []
for row in {arguments!r}:
    try:
        value = {call}
        observations.append(-1 if value is None else value)
    except RecursionError:
        observations.append("CALL_DEPTH")
    except IndexError:
        observations.append("ARRAY_BOUNDS")
    except ZeroDivisionError:
        observations.append("DIVISION_BY_ZERO")
print(json.dumps(observations))
""")
    return json.loads(command([sys.executable,str(script)],path))


def java(path, archive, revision, arguments):
    if archive=="lower":
        source, call = "LowerBound", "new LowerBound().find(cells,row[0])"
        extras = ["SearchAlgorithm.java"]
    else:
        source, call = "HowManyTimesRotated", "HowManyTimesRotated.rotated(Arrays.copyOfRange(row,1,1+row[0]))"
        extras = []
    copyfile(UPSTREAM/f"{archive}-{revision}.java",path/f"{source}.java")
    for filename in extras:
        copyfile(UPSTREAM/filename,path/filename)
    examples = "{"+",".join("{"+",".join(map(str,row))+"}" for row in arguments)+"}"
    (path/"Harness.java").write_text(f"""package com.thealgorithms.searches;
import java.util.Arrays;
public class Harness {{
    public static void main(String[] args) {{
        int[][] rows = {examples};
        for (int[] row : rows) {{
            Integer[] cells = Arrays.stream(row).skip(1).boxed().toArray(Integer[]::new);
            try {{ System.out.println({call}); }}
            catch (IndexOutOfBoundsException err) {{ System.out.println("ARRAY_BOUNDS"); }}
        }}
    }}
}}
""")
    jar = os.getenv("PHASE10_ECJ_JAR")
    if jar:
        javac = ["java","-jar",str(Path(jar).resolve()),"-17","-proc:none"]
    elif which("javac"):
        javac = ["javac","-proc:none"]
    else:
        raise RuntimeError("Install javac or set PHASE10_ECJ_JAR")
    classes = path/"classes"
    classes.mkdir()
    command([*javac,"-d",str(classes),f"{source}.java","Harness.java",*extras],path)
    lines = command(["java","-cp",str(classes),"com.thealgorithms.searches.Harness"],path)
    return ["ARRAY_BOUNDS" if line=="ARRAY_BOUNDS" else json.loads(line) for line in lines.splitlines()]


def replay(cases):
    oracle = MiniCOracle()
    outputs = {}
    for row in cases:
        if row["fault_origin"]!="adapted-real-defect":
            continue
        repo,_,archive,*_ = EXTERNAL[row["family"]]
        outcomes = {}
        discovery = row["vectors"]
        tests = discovery+row["holdout_vectors"]
        for revision,code in (("before",row["source"]),("after",row["references"][0])):
            with TemporaryDirectory(prefix="p10-upstream-") as workspace:
                runner = java if repo==JAVA else python
                upstream = runner(Path(workspace),archive,revision,[vector["arguments"] for vector in tests])
            adapted = []
            for test in tests:
                report = oracle.verify(code,"f",(Vector.model_validate(test),),ExecutionLimits())
                issue = report.execution.issue
                adapted.append(issue.code if issue else report.observations[0].actual)
            assert upstream==adapted,(row["id"],revision,upstream,adapted)
            outcomes[revision] = [
                {"partition":"discovery" if i<len(discovery) else "holdout","input":test["arguments"],
                 "expected":test["expected"],"upstream":original,"adapted":translation}
                for i,(test,original,translation) in enumerate(zip(tests,upstream,adapted,strict=True))
            ]
        assert any(item["upstream"]!=item["expected"] for item in outcomes["before"][:len(discovery)])
        assert all(item["upstream"]==item["expected"] for item in outcomes["after"])
        outputs[row["family"]] = outcomes
    return outputs


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write",action="store_true")
    args = parser.parse_args()
    rows, _ = audit()
    outputs = replay(rows)
    if args.write:
        (REPORTS/"phase10-upstream-v1.json").write_text(json.dumps(outputs,indent=2)+"\n")
    print(f"Replayed {len(outputs)} upstream pairs on {sum(len(pair['after']) for pair in outputs.values())} distinct family inputs")
