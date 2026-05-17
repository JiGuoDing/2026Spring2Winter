"""第一个网络程序：启动本地 HTTP 服务，并用 http.client 发起请求。

运行方式:
    python 00_intro/examples/http_request.py

预期输出:
    status=200
    body={"message": "hello from local server", "path": "/hello"}
"""

from __future__ import annotations

import http.client
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer


class DemoHandler(BaseHTTPRequestHandler):
    """提供一个最小的本地 HTTP 接口。"""

    def do_GET(self) -> None:
        if self.path != "/hello":
            self.send_error(404, "Not Found")
            return

        payload = json.dumps(
            {"message": "hello from local server", "path": self.path},
            ensure_ascii=False,
        ).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        # 避免标准库默认日志干扰教学输出。
        return


def start_server() -> HTTPServer:
    server = HTTPServer(("127.0.0.1", 0), DemoHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def fetch_demo(port: int) -> tuple[int, str]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        connection.request("GET", "/hello")
        response = connection.getresponse()
        body = response.read().decode("utf-8")
        return response.status, body
    finally:
        connection.close()


def main() -> None:
    server = start_server()
    try:
        time.sleep(0.05)
        status, body = fetch_demo(server.server_port)
        print(f"status={status}")
        print(f"body={body}")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
