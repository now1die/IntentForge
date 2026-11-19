"""Smoke-test the protected Unix socket from inside a local test container."""
import http.client
import json
import socket
from time import sleep


class UnixHTTP(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.settimeout(15)
        self.sock.connect("/tmp/intentforge-clang.sock")


def request(method, path, payload=None):
    connection = UnixHTTP("localhost", timeout=15)
    try:
        connection.request(method, path, json.dumps(payload) if payload else None,
                           {"Content-Type": "application/json"})
        response = connection.getresponse()
        return response.status, json.load(response)
    finally:
        connection.close()


def main():
    for _ in range(20):
        try:
            status, capability = request("GET", "/v1/c-analysis/capability")
            break
        except (FileNotFoundError, ConnectionRefusedError):
            sleep(.25)
    else:
        raise RuntimeError("The restricted service did not start")
    assert status == 200 and capability["status"] == "available", capability
    status, report = request("POST", "/v1/c-analysis", {"code": "int f(void){return 7;}"})
    assert status == 200 and report["status"] == "ok"
    assert any(node["kind"] == "FUNCTION_DECL" for node in report["units"][0]["nodes"])
    status, include = request("POST", "/v1/c-analysis", {"code": '#include "/etc/passwd"'})
    assert status == 200 and include["status"] == "compiler_errors"
    assert request("GET", "/health")[0] == 404
    print(json.dumps({"version": capability["version"], "c_analysis": report["status"],
                      "host_include": include["status"], "main_api_health": 404}))


if __name__ == "__main__":
    main()
