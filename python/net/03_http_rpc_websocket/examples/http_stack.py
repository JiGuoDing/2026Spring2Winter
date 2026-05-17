"""标准库 HTTP 服务端 + urllib.request / requests 客户端示例。

这个示例展示三件事：
1. 使用 http.server.BaseHTTPRequestHandler 构建简单路由。
2. 用装饰器模拟路由注册、中间件和请求钩子。
3. 使用 urllib.request 和 requests 调用本地 HTTP API。
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable

from urllib import request as urllib_request


RouteResult = tuple[int, dict[str, str], dict[str, object]]
RouteHandler = Callable[[BaseHTTPRequestHandler, dict[str, object]], RouteResult]

ROUTES: dict[tuple[str, str], RouteHandler] = {}
BEFORE_HOOKS: list[Callable[[BaseHTTPRequestHandler], None]] = []
AFTER_HOOKS: list[Callable[[BaseHTTPRequestHandler, int], None]] = []


def route(method: str, path: str) -> Callable[[RouteHandler], RouteHandler]:
    def decorator(func: RouteHandler) -> RouteHandler:
        ROUTES[(method.upper(), path)] = func
        return func

    return decorator


def before_request(func: Callable[[BaseHTTPRequestHandler], None]) -> Callable[[BaseHTTPRequestHandler], None]:
    BEFORE_HOOKS.append(func)
    return func


def after_request(func: Callable[[BaseHTTPRequestHandler, int], None]) -> Callable[[BaseHTTPRequestHandler, int], None]:
    AFTER_HOOKS.append(func)
    return func


def require_token(func: RouteHandler) -> RouteHandler:
    def wrapper(handler: BaseHTTPRequestHandler, payload: dict[str, object]) -> RouteResult:
        if handler.headers.get("X-Token") != "demo-token":
            return 401, {}, {"error": "missing or invalid token"}
        return func(handler, payload)

    return wrapper


@before_request
def capture_start_time(handler: BaseHTTPRequestHandler) -> None:
    handler.request_started_at = time.perf_counter()  # type: ignore[attr-defined]


@after_request
def log_request(handler: BaseHTTPRequestHandler, status_code: int) -> None:
    elapsed_ms = (time.perf_counter() - handler.request_started_at) * 1000  # type: ignore[attr-defined]
    print(f"{handler.command} {handler.path} -> {status_code} ({elapsed_ms:.2f} ms)")


@route("GET", "/health")
def health_check(handler: BaseHTTPRequestHandler, payload: dict[str, object]) -> RouteResult:
    return 200, {}, {"status": "ok"}


@route("POST", "/echo")
def echo_payload(handler: BaseHTTPRequestHandler, payload: dict[str, object]) -> RouteResult:
    return 201, {}, {"you_sent": payload}


@route("GET", "/secure")
@require_token
def secure_endpoint(handler: BaseHTTPRequestHandler, payload: dict[str, object]) -> RouteResult:
    return 200, {}, {"message": "token accepted"}


class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self._dispatch()

    def do_POST(self) -> None:
        self._dispatch()

    def _dispatch(self) -> None:
        payload = self._read_json_payload()
        for hook in BEFORE_HOOKS:
            hook(self)

        handler = ROUTES.get((self.command, self.path))
        if handler is None:
            status_code, headers, body = 404, {}, {"error": "not found"}
        else:
            status_code, headers, body = handler(self, payload)

        response_body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_body)))
        self.send_header("X-Elapsed-Ms", f"{(time.perf_counter() - self.request_started_at) * 1000:.2f}")  # type: ignore[attr-defined]
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(response_body)

        for hook in AFTER_HOOKS:
            hook(self, status_code)

    def _read_json_payload(self) -> dict[str, object]:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length == 0:
            return {}
        raw_body = self.rfile.read(content_length)
        if not raw_body:
            return {}
        return json.loads(raw_body.decode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:
        return


def start_server() -> HTTPServer:
    server = HTTPServer(("127.0.0.1", 0), AppHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def read_json_from_urllib(url: str, data: bytes | None = None, headers: dict[str, str] | None = None, method: str | None = None) -> dict[str, object]:
    request = urllib_request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib_request.urlopen(request, timeout=3) as response:
        return json.loads(response.read().decode("utf-8"))


def demo_urllib(port: int) -> None:
    base_url = f"http://127.0.0.1:{port}"
    print(f"urllib GET /health -> {read_json_from_urllib(base_url + '/health')}")

    payload = json.dumps({"name": "Python"}).encode("utf-8")
    echo = read_json_from_urllib(
        base_url + "/echo",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    print(f"urllib POST /echo -> {echo}")


def demo_requests(port: int) -> None:
    try:
        import requests
    except ImportError:
        print("requests 未安装，跳过 requests 示例。")
        return

    base_url = f"http://127.0.0.1:{port}"
    with requests.Session() as session:
        response = session.get(base_url + "/secure", headers={"X-Token": "demo-token"}, timeout=3)
        print(f"requests GET /secure -> {response.status_code}, {response.json()}")
        response = session.post(base_url + "/echo", json={"library": "requests"}, timeout=3)
        print(f"requests POST /echo -> {response.status_code}, {response.json()}")


def main() -> None:
    server = start_server()
    try:
        time.sleep(0.05)
        demo_urllib(server.server_port)
        demo_requests(server.server_port)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
