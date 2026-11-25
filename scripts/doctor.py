"""Check the local workbench without exposing environment values."""
import argparse
from html.parser import HTMLParser
from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
import re
from shutil import which
from subprocess import run
import sys
from urllib.error import URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
HTTP = build_opener(ProxyHandler({}))


class StartupScript(HTMLParser):
    def __init__(self):
        super().__init__()
        self.source = None

    def handle_starttag(self, tag, attrs):
        if tag=="script" and dict(attrs).get("type")=="module":
            self.source = dict(attrs).get("src")


def request(url, payload=None, *, read_limit=1_000_000):
    request = Request(url,data=json.dumps(payload).encode() if payload is not None else None,
                      headers={"Content-Type":"application/json"} if payload is not None else {})
    with HTTP.open(request,timeout=5) as response:
        return response.headers.get("Content-Type",""),response.read(read_limit)


def json_response(url, payload=None):
    response_type,body=request(url,payload)
    if "application/json" not in response_type:
        raise ValueError("Expected JSON")
    value=json.loads(body)
    if not isinstance(value,dict):
        raise ValueError("Expected a JSON object")
    return value


def dependency_status():
    packages=[]
    for name in ("fastapi","uvicorn","pydantic","scikit-learn"):
        try:
            packages.append(f"{name} {version(name)}")
        except PackageNotFoundError:
            return "Install Python dependencies with pip install -r requirements.txt.", False
    return ", ".join(packages), True


def node_status():
    node=which("node")
    if node is None:
        return "Node executable is missing.",False
    result=run([node,"--version"],text=True,capture_output=True,timeout=5,check=False)
    match=re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)\s*",result.stdout)
    if not match:
        return "Could not read the Node version.",False
    current=tuple(map(int,match.groups()))
    return f"Node {'.'.join(map(str,current))}",(20,19,0)<=current<(25,0,0)


def port(value):
    try:
        number=int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Expected a numeric TCP port") from None
    if not 1<=number<=65535:
        raise argparse.ArgumentTypeError("Expected a port between 1 and 65535")
    return number


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frontend-port",type=port,default=5173)
    parser.add_argument("--backend-port",type=port,default=8000)
    args=parser.parse_args()
    backend=f"http://127.0.0.1:{args.backend_port}"
    frontend=f"http://127.0.0.1:{args.frontend_port}"
    py_supported=sys.version_info[:2]==(3,12)
    node, node_ok=node_status()
    deps,deps_ok=dependency_status()
    frontend_deps=all((ROOT/"frontend"/"node_modules"/name/"package.json").is_file()
                      for name in ("vite","react","monaco-editor"))
    print(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
          + ("" if py_supported else " (use Python 3.12 for repository verification)"))
    print(node)
    print("Python dependencies",deps)
    print("Frontend dependencies", "installed" if frontend_deps else "run npm --prefix frontend ci")
    print("Frontend port",args.frontend_port,"Backend port",args.backend_port)
    print("API base","custom override configured" if os.environ.get("VITE_API_BASE_URL") else "same-origin /api by default")
    errors=(URLError,TimeoutError,OSError,ValueError)
    try:
        health = json_response(backend + "/health")
        reachable = health.get("status") == "ok"
        print("Backend API", "reachable" if reachable else "unexpected health response")
    except errors:
        print("Backend API unreachable")
        reachable = False
    backend_ok = False
    if reachable:
        try:
            compiler = json_response(backend + "/analyze", {"code": "int main(){return 0;}"})
            backend_ok = compiler.get("success") is True
        except errors:
            pass
        print("Mini-C compiler", "ready" if backend_ok else "analysis failed")
    frontend_ok = False
    try:
        content, body = request(frontend + "/")
        if "text/html" not in content:
            raise ValueError("Expected workbench HTML")
        print("Frontend HTML reachable")
    except errors:
        print("Frontend HTML unreachable or unexpected")
    else:
        try:
            startup = StartupScript()
            startup.feed(body.decode())
            asset = urljoin(frontend, startup.source or "")
            if not startup.source or urlsplit(asset).netloc != urlsplit(frontend).netloc:
                raise ValueError("Missing same-origin entry script")
            if "javascript" not in request(asset, read_limit=1024)[0]:
                raise ValueError("Expected JavaScript")
            frontend_ok = True
            print("Frontend entry JavaScript reachable")
        except errors:
            print("Frontend entry JavaScript unavailable")
    try:
        proxy_ok=json_response(frontend+"/api/health").get("status")=="ok"
    except errors:
        proxy_ok=False
    print("Same-origin API bridge", "ready" if proxy_ok else "unavailable")
    try:
        capability=json_response(backend+"/v1/behavioral-verification/capability").get("status")
    except errors:
        capability=None
    statuses={"available":"available","disabled":"analysis-only",
              "worker_unavailable":"worker disconnected","capacity_reached":"worker busy"}
    print("Optional interactive execution",statuses.get(capability,"unavailable"))
    return 0 if all((py_supported,node_ok,deps_ok,frontend_deps,backend_ok,frontend_ok,proxy_ok)) else 1


if __name__=="__main__":
    raise SystemExit(main())
