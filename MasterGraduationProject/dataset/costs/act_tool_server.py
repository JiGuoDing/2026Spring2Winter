"""真实本地只读 HTTP/JSON Tool Gateway（v0.6.0，模拟生产 MCP/REST 数据工具网关）。

特性：
  1. 标准 HTTP/1.1 POST 端点 /v1/tools/act/execute（JSON 请求/响应）；
  2. 有界只读连接池（queue.Queue, pool_size=4），每条连接以 mode=ro&immutable=1 打开
     dataset/db/scale/prod_scale.sqlite，并复核 db/executor.py 只读 SQL 正则；
  3. 完整 4 步生产工具链：
       auth_parse -> pool_wait -> schema_inspect -> sql_validate -> sql_execute -> result_serialize
  4. 全程零 time.sleep()，全部计时为真实物理 wall-clock（perf_counter）。
"""
from __future__ import annotations

import json
import queue
import re
import sqlite3
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "db"))

import compare  # noqa: E402
import executor  # noqa: E402

_TABLE_RE = re.compile(r"\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.IGNORECASE)
_PRIV = {"public": 1, "staff": 2, "restricted": 3}
MAX_ROWS = 500


def _extract_tables(sql: str) -> list[str]:
    seen: list[str] = []
    for m in _TABLE_RE.finditer(sql):
        tb = m.group(1)
        if tb not in seen:
            seen.append(tb)
    return seen or ["dim_date"]


class ReadOnlyPool:
    """有界只读 SQLite 连接池：高并发下产生真实排队延迟。"""

    def __init__(self, db_path: Path, pool_size: int = 4) -> None:
        self.db_path = db_path
        self.pool_size = pool_size
        self._q: queue.Queue[sqlite3.Connection] = queue.Queue(maxsize=pool_size)
        uri = f"file:{db_path.as_posix()}?mode=ro&immutable=1"
        for _ in range(pool_size):
            con = sqlite3.connect(uri, uri=True, check_same_thread=False)
            con.execute("PRAGMA query_only = ON")
            self._q.put(con)

    def acquire(self) -> tuple[sqlite3.Connection, float]:
        t0 = time.perf_counter()
        con = self._q.get()
        wait_ms = (time.perf_counter() - t0) * 1000.0
        return con, wait_ms

    def release(self, con: sqlite3.Connection) -> None:
        self._q.put(con)

    def close_all(self) -> None:
        while not self._q.empty():
            con = self._q.get_nowait()
            con.close()


def _run_select(con: sqlite3.Connection, sql: str) -> tuple[list[str], list[tuple]]:
    cur = con.execute(sql)
    cols = [d[0] for d in (cur.description or ())]
    rows = cur.fetchmany(MAX_ROWS)
    cur.close()
    return cols, rows


def start_gateway(db_path: Path, pool_size: int = 4) -> tuple[ThreadingHTTPServer, threading.Thread, ReadOnlyPool, int]:
    pool = ReadOnlyPool(db_path, pool_size=pool_size)

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format: str, *args) -> None:  # noqa: A002
            return

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/v1/tools/act/execute":
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return

            t_auth0 = time.perf_counter()
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            body = json.loads(raw.decode("utf-8"))
            perm = body.get("permission", "public")
            sql = str(body.get("sql", "")).strip()
            difficulty = str(body.get("difficulty", "single_table"))

            if perm not in _PRIV:
                self._send_json(403, {"error": "invalid permission"})
                return
            err = executor.validate_readonly_sql(sql) if hasattr(executor, "validate_readonly_sql") else None
            if err or not re.match(r"^(SELECT|WITH)\b", sql, re.IGNORECASE):
                self._send_json(400, {"error": err or "only SELECT/WITH allowed"})
                return
            tables = _extract_tables(sql)
            t_auth_ms = (time.perf_counter() - t_auth0) * 1000.0

            con, t_wait_ms = pool.acquire()
            try:
                # 1) schema_inspect（记录主表列名供后续真实口径/质量探查使用）
                t0 = time.perf_counter()
                table_cols: dict[str, set[str]] = {}
                for tb in tables:
                    _, sc_rows = _run_select(con, f"SELECT name, type, [notnull], pk FROM pragma_table_info('{tb}')")
                    table_cols[tb] = {str(r[0]) for r in sc_rows}
                t_inspect_ms = (time.perf_counter() - t0) * 1000.0

                # 2) sql_validate
                t0 = time.perf_counter()
                _run_select(con, f"SELECT * FROM ({sql.rstrip(';')}) LIMIT 0")
                t_val_ms = (time.perf_counter() - t0) * 1000.0

                # 3) sql_execute（复杂题追加真实 BI 口径与分区完整性只读核验 SQL）
                t0 = time.perf_counter()
                main_tb = tables[0]
                mcols = table_cols.get(main_tb, set())
                if difficulty in ("join", "nested_agg"):
                    if "date_key" in mcols:
                        _run_select(con, f'SELECT "date_key", COUNT(*) AS cnt FROM "{main_tb}" GROUP BY "date_key"')
                    if "is_deleted" in mcols and "currency_code" in mcols:
                        _run_select(
                            con,
                            f'SELECT "is_deleted", "currency_code", COUNT(*) AS cnt FROM "{main_tb}" '
                            f'GROUP BY "is_deleted", "currency_code"',
                        )
                    elif "status" in mcols:
                        _run_select(con, f'SELECT "status", COUNT(*) AS cnt FROM "{main_tb}" GROUP BY "status"')
                    else:
                        _run_select(con, f'SELECT COUNT(*) AS cnt FROM "{main_tb}"')
                cols, rows = _run_select(con, sql)
                t_exec_ms = (time.perf_counter() - t0) * 1000.0
            finally:
                pool.release(con)

            # 4) result_check & JSON 序列化
            t0 = time.perf_counter()
            norm = compare.normalize({"columns": cols, "rows": [list(r) for r in rows]})
            resp_obj = {
                "ok": True,
                "row_count": len(norm["rows"]),
                "columns": norm["columns"],
                "preview": norm["rows"][:20],
                "server_timings_ms": {
                    "auth_parse": round(t_auth_ms, 4),
                    "pool_wait": round(t_wait_ms, 4),
                    "schema_inspect": round(t_inspect_ms, 4),
                    "sql_validate": round(t_val_ms, 4),
                    "sql_execute": round(t_exec_ms, 4),
                },
            }
            payload = json.dumps(resp_obj, ensure_ascii=False).encode("utf-8")
            t_ser_ms = (time.perf_counter() - t0) * 1000.0
            resp_obj["server_timings_ms"]["result_serialize"] = round(t_ser_ms, 4)
            payload = json.dumps(resp_obj, ensure_ascii=False).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _send_json(self, code: int, obj: dict) -> None:
            payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    class GatewayHTTPServer(ThreadingHTTPServer):
        request_queue_size = 128
        daemon_threads = True

    srv = GatewayHTTPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    return srv, th, pool, port
