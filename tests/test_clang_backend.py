import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from clang_backend import adapter
from clang_backend.worker import supported_version


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def enabled():
    if not os.getenv("INTENTFORGE_LIBCLANG"):
        pytest.skip("Optional libclang configuration is absent.")
    cap = adapter.capability()
    assert cap.status == "available", cap.detail
    assert cap.version.startswith("19.")
    return cap


def test_unavailable_is_additive(client, monkeypatch):
    monkeypatch.delenv("INTENTFORGE_CLANG_MODE", raising=False)
    assert client.get("/v1/c-analysis/capability").json()["status"] == "unavailable"
    assert client.post("/v1/c-analysis", json={"code": "int x;"}).json()["status"] == "unavailable"
    assert client.post("/analyze", json={"code": "int f(){return 0;}"}).json()["success"]
    assert client.post("/v1/intention-analysis", json={"code": "int f(){return 0;}"}).status_code == 200


def test_missing_and_unsupported_library(monkeypatch):
    monkeypatch.setenv("INTENTFORGE_CLANG_MODE", "isolated")
    monkeypatch.setenv("INTENTFORGE_LIBCLANG", "/no/libclang.so")
    assert adapter.capability().status == "unavailable"
    monkeypatch.setenv("INTENTFORGE_LIBCLANG", str(Path("/bin/sh").resolve()))
    assert adapter.capability().status == "unavailable"
    version17 = Path("/usr/lib/llvm-17/lib/libclang.so.1")
    if version17.exists():
        monkeypatch.setenv("INTENTFORGE_LIBCLANG", str(version17))
        assert adapter.capability().status == "unavailable"


@pytest.mark.parametrize(("version", "accepted"), [
    ("Debian clang version 19.1.7", "19.1.7"),
    ("Ubuntu clang version 19.1.1 (release)", "19.1.1"),
    ("clang version 18.1.8", None),
    ("clang version 20.1.0", None),
])
def test_supported_version(version, accepted):
    assert supported_version(version) == accepted


def test_limits_at_transport(client):
    response = client.post("/v1/c-analysis", content=b"x" * 640_001)
    assert response.status_code == 413
    for request in ({"files": {"a.c": ""}}, {"code": "", "flags": ["-I/"]},
                    {"files": {"a.c": ""}, "translation_units": [], "code": ""}):
        assert client.post("/v1/c-analysis", json=request).status_code == 422


def test_validation_and_worker_limits(enabled, client, monkeypatch, tmp_path):
    for name in ("../bad.c", "/etc/x.h", "x/../p.c", "a\\b.c", "x.cpp"):
        assert adapter.analyze({name: ""}, [name], "c17").status == "unsupported_configuration"
    assert adapter.analyze({"x.c": "é" * 49_000}, ["x.c"], "c17").status == "request_limit"
    assert adapter.analyze({"x.c": ""}, ["x.c"], "c++11").status == "unsupported_configuration"
    script = tmp_path / "stub.py"
    monkeypatch.setattr(adapter, "WORKER", script)
    script.write_text("import time; time.sleep(10)")
    with pytest.raises(adapter.WorkerError, match="time limit"):
        adapter._run([], tmp_path, timeout=.15)
    script.write_text("print('x' * 100_000)")
    with pytest.raises(adapter.WorkerError, match="output limit"):
        adapter._run([], tmp_path, limit=1024)


def call(client, code):
    response = client.post("/v1/c-analysis", json={"code": code})
    assert response.status_code == 200
    return response.json()


@pytest.mark.parametrize(("source", "status", "phase"), [
    ("int f(void) { return 1 }", "syntax_errors", "syntax"),
    ("int f(void) { return missing; }", "semantic_errors", "semantic"),
    ("#include \"missing.h\"\nint x;", "compiler_errors", "preprocessing"),
])
def test_structured_diagnostics(enabled, client, source, status, phase):
    result = call(client, source)
    assert result["status"] == status, result
    unit = result["units"][0]
    assert unit["ast"] == "partial"
    diag = unit["diagnostics"][0]
    assert diag["phase"] == phase and diag["span"]["file"] == "main.c"
    assert diag["category"] and diag["severity"] in {"error", "fatal"}


def test_unicode_and_macro_locations(enabled, client):
    source = "/*😀é*/ int x = missing;"
    diag = call(client, source)["units"][0]["diagnostics"][0]
    start = diag["span"]["start"]
    prefix = source.split("missing")[0]
    assert start == {"byte_offset": len(prefix.encode()), "line": 1,
                     "column": len(prefix.encode("utf-16-le")) // 2 + 1}
    macro = call(client, "#define VALUE 2\n#line 999 \"fake.c\"\nint x = VALUE;")["units"][0]
    expansion = next(node for node in macro["nodes"] if node["kind"] == "MACRO_INSTANTIATION")
    assert expansion["span"]["file"] == "main.c"
    assert expansion["span"]["start"]["line"] == 3


def test_c_constructs_and_multiple_translation_units(enabled, client):
    files = {
        "inc/types.h": """typedef unsigned long size_type;
        typedef struct Item { int values[2][3]; union { double d; long bits; } cast; } Item;
        enum Mode { FIRST, LAST };
        void *malloc(size_type);
        void free(void *);
        #define WIDTH 3
        int apply(Item *, int (*)(int), enum Mode);
        """,
        "src/calc.c": """#include "inc/types.h"
        static int recur(int n) { if (n < 2) return n; return n * recur(n-1); }
        int apply(Item *item, int (*callback)(int), enum Mode mode) {
          double scaled = (double) item->cast.bits;
          void *buffer = malloc(sizeof(Item)); free(buffer);
          for (int i = 0; i < WIDTH; ++i) { int scaled = i; if (scaled == mode) return callback(item->values[0][i]); }
          return recur((int) scaled);
        }""",
        "src/entry.c": """#include "inc/types.h"
        static int negate(int n) { return -n; }
        int entry(void) { Item value = {0}; return apply(&value, negate, FIRST); }""",
    }
    result = client.post("/v1/c-analysis", json={"files": files,
                         "translation_units": ["src/calc.c", "src/entry.c"]}).json()
    assert result["status"] == "ok", result
    assert [unit["entry"] for unit in result["units"]] == ["src/calc.c", "src/entry.c"]
    for unit in result["units"]:
        assert unit["ast"] == "available"
        node_map = {node["id"]: node for node in unit["nodes"]}
        assert all(node["parent"] is None or node["parent"] in node_map for node in node_map.values())
        assert all(node["reference"] is None or node_map[node["reference"]]["declaration"] for node in node_map.values())
        assert any(node["reference"] is not None and node["scope"] is not None for node in node_map.values())
        assert any(node["kind"] == "STRUCT_DECL" and node["span"]["file"] == "inc/types.h"
                   for node in node_map.values())
    calc = result["units"][0]["nodes"]
    assert {"FOR_STMT", "CSTYLE_CAST_EXPR", "UNION_DECL", "ENUM_DECL", "MACRO_INSTANTIATION"} <= {
        node["kind"] for node in calc}
    apply = next(node for node in calc if node["name"] == "apply" and node["kind"] == "FUNCTION_DECL")
    assert apply["parameter_types"] == ["Item *", "int (*)(int)", "enum Mode"]
    assert apply["result_type"] == "int"


def test_host_sources_are_inaccessible(enabled, client, tmp_path):
    sentinel = tmp_path / "sentinel.h"
    sentinel.write_text("#error CONTENT_OF_HOST_FILE_MUST_NEVER_BE_SEEN")
    result = call(client, f'#define TARGET "{sentinel}"\n#if __has_include(TARGET)\n#error HOST_PATH_VISIBLE\n#endif\n#include TARGET')
    diagnostics = [diag["message"] for diag in result["units"][0]["diagnostics"]]
    assert diagnostics and any("file not found" in message for message in diagnostics)
    assert all("CONTENT_OF_HOST" not in message and "HOST_PATH_VISIBLE" not in message for message in diagnostics)
    embed = client.post("/v1/c-analysis", json={"standard": "c23",
                        "code": f'unsigned char bytes[] = {{\n#embed "{sentinel}"\n}};'}).json()
    assert embed["status"] != "ok"
