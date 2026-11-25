"""Compare original-language revision pairs with finite scalar adaptations."""
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from ai.behavior_oracle import ExecutionLimits, Vector
from vm.behavioral_executor import MiniCOracle
from .phase13_fixtures import PINS, ROOT, fixtures
from .phase13_audit import audit

PYTHON_DRIVER = """
import json,runpy,sys
fn=runpy.run_path("specimen.py")[sys.argv[1]]
values=[]
for args in json.load(sys.stdin):
    try:
        if sys.argv[1] in ("find_max","tim_sort"):
            result=fn(args[1:][:args[0]])
            if isinstance(result,list): result=result[0] if result else -82
        elif sys.argv[1]=="generate_all_combinations": result=len(fn(*args))
        else: result=fn(*args)
    except IndexError:
        result=-98 if sys.argv[1]=="find_max" else -81
    except ValueError:
        result=-99 if sys.argv[1]=="find_max" else -73
    values.append(result)
print(json.dumps(values))
"""
FUNCTIONS = {"digit-count":"num_digits","combination-domain":"generate_all_combinations",
             "empty-timsort":"tim_sort","empty-maximum":"find_max"}


def original(family, phase, inputs, folder):
    source = (ROOT/"upstream"/f"{family}-{phase}.txt").read_text()
    if family in FUNCTIONS:
        (folder/"specimen.py").write_text(source)
        cmd = [sys.executable,"-I","-B","-c",PYTHON_DRIVER,FUNCTIONS[family]]
    else:
        if family == "bucket-order":
            source = source.split("// Testing")[0]
            expression = "bucketSort(args,100)[0]"
        elif family == "hex-channel":
            source = source.split("console.log")[0]
            expression = "hexStringToRGB(args.map(n=>n.toString(16)).join('')).g"
        else:
            source = source.split("var num =")[0].split("const rl =")[0]
            expression = "multiplesThreeAndFive(args[0])"
        driver = "const rows=JSON.parse(require('node:fs').readFileSync(0,'utf8'));"
        (folder/"specimen.cjs").write_text(source+"\n"+driver+"console.log(JSON.stringify(rows.map(args=>"+expression+")));")
        cmd = ["node","--permission","--allow-fs-read="+str(folder),"specimen.cjs"]
    proc = subprocess.run(cmd,cwd=folder,input=json.dumps(inputs),text=True,capture_output=True,check=True,timeout=8)
    return json.loads(proc.stdout)


def replay():
    audit()
    oracle = MiniCOracle()
    result = {}
    for row in fixtures():
        family = row["family"]
        if family not in PINS or row["disposition"] != "fault":
            continue
        vectors = row["vectors"] + row["holdout_vectors"]
        pairs = {}
        for phase, code in (("before",row["source"]),("after",row["references"][0])):
            with TemporaryDirectory() as folder:
                native = original(family,phase,[v["arguments"] for v in vectors],Path(folder))
            adapted = [oracle.verify(code,"f",(Vector.model_validate(v),),ExecutionLimits()).observations[0].actual
                       for v in vectors]
            assert native == adapted,(family,phase,native,adapted)
            if phase=="after":
                assert native == [v["expected"] for v in vectors]
            pairs[phase] = native
        result[family] = {"inputs":[v["arguments"] for v in vectors], **pairs}
    return result


if __name__=="__main__":
    print(json.dumps(replay(),indent=2))
