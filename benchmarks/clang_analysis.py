"""Measure compiler evidence through the versioned C analysis API."""
import argparse
import json
from pathlib import Path
from time import perf_counter

from fastapi.testclient import TestClient

from backend.app.main import app
from .phase25_evaluate import timing

REPORT = Path(__file__).with_name("reports") / "clang-analysis-v1.json"
CASES = (
    ("pointers", {"code": "int get(const int *p){return *p;}"}, "ok", "PARM_DECL", None),
    ("struct_and_cast", {"code": "struct P{double value;};int f(struct P *p){return (int)p->value;}"}, "ok", "CSTYLE_CAST_EXPR", None),
    ("c23_bool", {"standard": "c23", "code": "bool present(void){return true;}"}, "ok", "FUNCTION_DECL", None),
    ("array_layout", {"code": "int pixels[3][4]; int f(int i){return pixels[i][1];}"}, "ok", "ARRAY_SUBSCRIPT_EXPR", None),
    ("syntax", {"code": "int x = ;"}, "syntax_errors", "VAR_DECL", (1, 9)),
    ("unknown_binding", {"code": "/*😀*/ int x = q;"}, "semantic_errors", "VAR_DECL", (1, 16)),
    ("bad_pointer", {"code": "int f(int i){return *i;}"}, "semantic_errors", "FUNCTION_DECL", (1, 21)),
    ("missing_field", {"code": "struct P{int x;}; int f(struct P p){return p.y;}"}, "semantic_errors", "STRUCT_DECL", (1, 46)),
    ("signature", {"code": "void g(int a,int b);void f(void){g(1);}"}, "semantic_errors", "FUNCTION_DECL", (1, 37)),
    ("missing_header", {"code": "#include \"unknown.h\"\nint x;"}, "compiler_errors", "INCLUSION_DIRECTIVE", (1, 10)),
    ("nested_header", {"files": {"headers/types.h": "typedef long index_t;", "src/a.c":
                    "#include \"headers/types.h\"\nindex_t read(void){return 42;}"},
                    "translation_units": ["src/a.c"]}, "ok", "TYPEDEF_DECL", None),
    ("multiple_units", {"files": {"shared.h": "#define COUNT 3", "a.c": "#include \"shared.h\"\nint a=COUNT;",
                        "b.c": "#include \"shared.h\"\nint b(void){return COUNT;}"},
                        "translation_units": ["a.c", "b.c"]}, "ok", "MACRO_INSTANTIATION", None),
)


def run():
    rows, times = [], []
    with TestClient(app) as client:
        capability = client.get("/v1/c-analysis/capability").json()
        if capability["status"] != "available":
            output = client.post("/v1/c-analysis", json={"code": "int a;"})
            return {"available": False, "unavailable_http": output.status_code,
                    "unavailable_status": output.json()["status"],
                    "mini_c_operational": client.post("/analyze", json={"code": "int a;"}).status_code == 200}
        for name, request, expected, node_kind, span in CASES:
            started = perf_counter()
            response = client.post("/v1/c-analysis", json=request)
            times.append((perf_counter() - started) * 1000)
            response.raise_for_status()
            result = response.json()
            units = result["units"]
            diagnostics = [diag for unit in units for diag in unit["diagnostics"] if diag["severity"] in ("fatal", "error")]
            first = diagnostics[0]["span"]["start"] if diagnostics and diagnostics[0]["span"] else None
            actual_span = [first["line"], first["column"]] if first else None
            rows.append({"case": name, "http": response.status_code, "expected_status": expected, "status": result["status"],
                         "ast_units_with_evidence": sum(any(node["kind"] == node_kind for node in unit["nodes"]) for unit in units),
                         "ast_units": len(units), "expected_span": list(span) if span else None, "span": actual_span})
    return {"available": True, "version": capability["version"], "latency_ms": timing(times), "cases": rows}


def verify(report):
    if not report["available"]:
        return report == {"available": False, "unavailable_http": 200, "unavailable_status": "unavailable",
                          "mini_c_operational": True}
    return all(row["http"] == 200 and row["status"] == row["expected_status"] and row["span"] == row["expected_span"]
               and row["ast_units"] > 0 and row["ast_units_with_evidence"] == row["ast_units"] for row in report["cases"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    report = run()
    serialized = json.dumps(report, indent=2) + "\n"
    if args.write:
        REPORT.write_text(serialized)
    print(serialized, end="")
    raise SystemExit(args.check and not verify(report))
