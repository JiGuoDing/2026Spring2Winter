"""Flask REST API 示例。

如果环境中安装了 Flask，这个脚本会启动一个最小 REST 服务，展示：
- 路由装饰器
- before_request / after_request 钩子
- JSON 请求与响应
"""

from __future__ import annotations

from time import perf_counter


def create_app():
    try:
        from flask import Flask, g, jsonify, request
    except ImportError as exc:  # pragma: no cover - 运行时提示
        raise RuntimeError("请先安装 Flask：pip install flask") from exc

    app = Flask(__name__)

    @app.before_request
    def capture_start_time() -> None:
        g.started_at = perf_counter()

    @app.after_request
    def add_elapsed_header(response):
        response.headers["X-Elapsed-Ms"] = f"{(perf_counter() - g.started_at) * 1000:.2f}"
        return response

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.post("/users")
    def create_user():
        payload = request.get_json(force=True)
        return jsonify(id=1, name=payload["name"]), 201

    return app


def main() -> None:
    try:
        app = create_app()
    except RuntimeError as exc:
        print(exc)
        return
    app.run(host="127.0.0.1", port=5000, debug=True)


if __name__ == "__main__":
    main()
