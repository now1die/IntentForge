"""Disposable libclang worker. All source buffers are supplied in memory."""
from bisect import bisect_right
import ctypes as ct
import errno
import json
import os
from pathlib import Path
import re
import resource
import sys

try:
    from clang import cindex as cx
except ImportError:
    cx = None

SEVERITIES = {1: "note", 2: "warning", 3: "error", 4: "fatal"}
SCOPES = {"FUNCTION_DECL", "COMPOUND_STMT", "FOR_STMT", "STRUCT_DECL", "UNION_DECL", "ENUM_DECL"}
MAX_NODES = 3500


def sandbox():
    """Preload the sandbox library, then deny filesystem, program and network I/O."""
    lib = ct.CDLL("libseccomp.so.2")
    lib.seccomp_init.argtypes = [ct.c_uint32]
    lib.seccomp_init.restype = ct.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ct.c_char_p]
    lib.seccomp_rule_add.argtypes = [ct.c_void_p, ct.c_uint32, ct.c_int, ct.c_uint]
    lib.seccomp_load.argtypes = [ct.c_void_p]
    lib.seccomp_release.argtypes = [ct.c_void_p]
    rules = lib.seccomp_init(0x00050000 | errno.ENOENT)
    if not rules:
        raise OSError("Could not initialize seccomp.")
    try:
        for name in (
            "brk", "mmap", "mmap2", "munmap", "mremap", "mprotect", "madvise",
            "fstat", "lseek", "read", "write", "writev", "close", "fcntl",
            "clock_gettime", "gettimeofday", "getrandom", "getcwd", "getpid", "gettid",
            "futex", "sched_yield", "sched_getaffinity", "prlimit64", "sigaltstack",
            "rt_sigaction", "rt_sigprocmask", "rt_sigreturn", "exit", "exit_group",
        ):
            number = lib.seccomp_syscall_resolve_name(name.encode())
            if number >= 0 and lib.seccomp_rule_add(rules, 0x7FFF0000, number, 0):
                raise OSError("Could not configure seccomp.")
        if lib.seccomp_load(rules):
            raise OSError("Could not activate seccomp.")
    finally:
        lib.seccomp_release(rules)


def configure(library):
    if cx is None:
        return None
    cx.Config.set_library_file(library)
    api = cx.conf.lib
    api.clang_getClangVersion.argtypes = []
    api.clang_getClangVersion.restype = cx._CXString
    api.clang_getClangVersion.errcheck = cx._CXString.from_result
    for name in ("clang_getExpansionLocation", "clang_getSpellingLocation"):
        getter = getattr(api, name)
        getter.argtypes = [cx.SourceLocation, ct.POINTER(cx.c_object_p), *([ct.POINTER(ct.c_uint)] * 3)]
        getter.restype = None
    version = re.search(r"clang version (\d+\.\d+\.\d+)", api.clang_getClangVersion())
    return version[1] if version and version[1].split(".")[0] == "19" else None


class Sources:
    def __init__(self, files):
        self.contents = {"/project/" + key: source.encode() for key, source in files.items()}
        self.lines = {key: [0, *(ending.end() for ending in re.finditer(rb"\r\n|\r|\n", source))]
                      for key, source in self.contents.items()}

    def position(self, loc, origin):
        file, line, column, offset = cx.c_object_p(), ct.c_uint(), ct.c_uint(), ct.c_uint()
        getter = (cx.conf.lib.clang_getSpellingLocation if origin == "spelling"
                  else cx.conf.lib.clang_getExpansionLocation)
        getter(loc, ct.byref(file), ct.byref(line), ct.byref(column), ct.byref(offset))
        path = cx.File(file).name if file else None
        if path not in self.contents or offset.value > len(self.contents[path]):
            return None
        starts = self.lines[path]
        line = bisect_right(starts, offset.value)
        prefix = self.contents[path][starts[line - 1]:offset.value]
        units = len(prefix.decode("utf-8", errors="ignore").encode("utf-16-le")) // 2
        return path.removeprefix("/project/"), {"line": line, "column": units + 1, "byte_offset": offset.value}

    def span(self, first, last=None, origin="expansion"):
        start = self.position(first, origin)
        end = self.position(last, origin) if last is not None else start
        if start and end and start[0] == end[0] and start[1]["byte_offset"] <= end[1]["byte_offset"]:
            return {"file": start[0], "start": start[1], "end": end[1], "origin": origin}
        return None

    def diagnostic(self, diag, depth=0):
        category = diag.category_name or None
        phase = {"Parse Issue": "syntax", "Lexical or Preprocessor Issue": "preprocessing",
                 "Semantic Issue": "semantic"}.get(category, "unclassified")
        related = [span for item in diag.ranges if (span := self.span(item.start, item.end))]
        anchor = self.span(diag.location)
        primary = next((span for span in related if anchor and span["file"] == anchor["file"]
                        and span["start"]["byte_offset"] <= anchor["start"]["byte_offset"] < span["end"]["byte_offset"]),
                       anchor)
        # The diagnostic can echo an include spelling. The worker only opens supplied buffers.
        return {"severity": SEVERITIES.get(diag.severity, "note"), "message": diag.spelling[:2000],
                "category": category, "code": diag.option or None, "phase": phase, "span": primary,
                "related": related[:12],
                "notes": [self.diagnostic(note, depth + 1) for note in list(diag.children)[:12]] if depth < 2 else []}

    def nodes(self, unit):
        rows, references, declarations = [], {}, {}
        stack = [(unit.cursor, None, None)]
        while stack and len(rows) < MAX_NODES:
            cursor, parent, scope = stack.pop()
            kind = cursor.kind.name
            point = self.span(cursor.location)
            if point is None and kind != "TRANSLATION_UNIT":
                continue
            span = self.span(cursor.extent.start, cursor.extent.end) or point
            spelling = self.span(cursor.extent.start, cursor.extent.end, "spelling")
            if spelling and span and all(spelling[key] == span[key] for key in ("file", "start", "end")):
                span["origin"] = "physical"
                spelling = None
            node_id = len(rows)
            decl = cursor.kind.is_declaration()
            name = cursor.spelling[:256] or None
            row = {"id": node_id, "kind": kind, "parent": parent, "scope": scope, "name": name,
                   "declaration": decl, "span": span, "spelling_span": spelling}
            if cursor.type.kind != cx.TypeKind.INVALID:
                row.update(type=cursor.type.spelling[:512], canonical_type=cursor.type.get_canonical().spelling[:512])
            if kind == "FUNCTION_DECL":
                row.update(parameter_types=[arg.type.spelling[:512] for arg in cursor.get_arguments()],
                           result_type=cursor.result_type.spelling[:512], variadic=cursor.type.is_function_variadic()
                           if cursor.type.kind == cx.TypeKind.FUNCTIONPROTO else None)
            if decl:
                usr = cursor.get_usr()
                if usr:
                    declarations.setdefault(usr, node_id)
            elif cursor.kind.is_reference() or kind in {"DECL_REF_EXPR", "MEMBER_REF_EXPR", "CALL_EXPR"}:
                target = cursor.referenced
                if target is not None:
                    references[node_id] = target.get_usr()
            rows.append(row)
            if kind in SCOPES:
                scope = node_id
            stack.extend((child, node_id, scope) for child in reversed(list(cursor.get_children())))
        for index, usr in references.items():
            rows[index]["reference"] = declarations.get(usr)
        return rows, bool(stack)


def collect(request):
    sources = Sources(request["files"])
    flags = ["-x", "c", "-std=" + request["standard"], "-fsyntax-only", "-nostdinc", "-I/project",
             "-fno-modules", "-Wno-invalid-command-line-argument", "-Wall", "-Wextra", "-ferror-limit=25"]
    units, failure_phases = [], set()
    index = cx.Index.create()
    for entry in request["entries"]:
        try:
            unit = index.parse("/project/" + entry, args=flags, unsaved_files=list(sources.contents.items()),
                               options=cx.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
        except cx.TranslationUnitLoadError:
            units.append({"entry": entry, "ast": "unavailable", "diagnostics": [], "nodes": []})
            failure_phases.add("unclassified")
            continue
        diagnostics = [sources.diagnostic(diag) for diag in unit.diagnostics if diag.severity]
        errors = {diag["phase"] for diag in diagnostics if diag["severity"] in {"error", "fatal"}}
        failure_phases.update(errors)
        rows, truncated = sources.nodes(unit)
        units.append({"entry": entry, "ast": "partial" if errors or truncated else "available",
                      "diagnostics": diagnostics, "nodes": rows})
    status = ("syntax_errors" if "syntax" in failure_phases else "semantic_errors" if failure_phases == {"semantic"}
              else "compiler_errors" if failure_phases else "ok")
    return {"status": status, "units": units}


def main():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    resource.setrlimit(resource.RLIMIT_AS, (640 * 1024 * 1024,) * 2)
    request = json.loads(Path("request.json").read_bytes()) if sys.argv[2] == "analyze" else None
    version = configure(sys.argv[1])
    if not version:
        result = {"status": "unavailable", "detail": "Clang requires libclang 19 and its Python bindings."}
    else:
        # Clang's crash recovery normally creates a worker thread. Run on the
        # process thread and let the parent handle worker exits and deadlines.
        cx.conf.lib.clang_toggleCrashRecovery(0)
        os.environ["LIBCLANG_NOTHREADS"] = "1"
        # Load the UTF-16 codec before restricting filesystem access.
        "".encode("utf-16-le")
        try:
            sandbox()
        except (OSError, AttributeError):
            result = {"status": "unavailable", "detail": "The Linux seccomp isolation policy could not be activated."}
        else:
            probe = request or {"files": {"probe.c": "int f(void) { return 42; }"}, "entries": ["probe.c"], "standard": "c23"}
            result = collect(probe)
            if request is None:
                available = result["status"] == "ok" and bool(result["units"][0]["nodes"])
                result = {"status": "available" if available else "unavailable", "version": version,
                          "detail": "Clang parses submitted buffers in a restricted worker." if available
                          else "Clang could not parse the isolated capability probe."}
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
