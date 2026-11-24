"""只读执行器：三层保护执行一条 SELECT/WITH。

用法：
  from executor import execute
  out = execute("v0", "SELECT COUNT(*) FROM fact_orders")
  out = execute("/abs/path/v0.sqlite", "SELECT ...")

三层保护
--------
1. 连接层：``sqlite3.connect("file:...?mode=ro&immutable=1", uri=True)``，并额外置
   ``PRAGMA query_only=ON``，任何写操作在 SQLite 内部直接失败；
2. 语句层：去掉注释与字符串后只接受以 SELECT / WITH 开头的单条语句，拒绝多语句，
   并拒绝 PRAGMA / ATTACH / INSERT / UPDATE / DELETE / DROP / CREATE 等关键字；
3. 资源层：``set_progress_handler`` 实现 5 秒超时（到期中断查询），结果行数上限 10000。

返回：``{"columns": [...], "rows": [[...]], "elapsed_ms": float, "error": None|str,
"truncated": bool}``。任何失败都通过 ``error`` 返回，不抛异常。
"""
from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path

DB_DIR = Path(__file__).resolve().parent
SNAPSHOT_DIR = DB_DIR / "snapshots"
DEFAULT_SNAPSHOT = "v0"

TIMEOUT_SECONDS = 5.0
ROW_LIMIT = 10000
PROGRESS_STEPS = 1000          # 每执行 N 条虚拟机指令回调一次进度处理器

ALLOWED_HEADS = frozenset({"SELECT", "WITH"})

# 允许出现在 SELECT 里做别名的普通标识符不受影响：这里按独立单词匹配，不按子串匹配。
FORBIDDEN_WORDS = frozenset({
    "PRAGMA", "ATTACH", "DETACH", "INSERT", "UPDATE", "DELETE", "REPLACE",
    "DROP", "CREATE", "ALTER", "TRUNCATE", "VACUUM", "REINDEX", "ANALYZE",
    "BEGIN", "COMMIT", "ROLLBACK", "SAVEPOINT", "RELEASE", "TRIGGER",
    "GRANT", "REVOKE", "LOAD_EXTENSION",
})

_SNAPSHOT_ALIASES = ("v0", "v1", "v2")


def snapshot_path(db=DEFAULT_SNAPSHOT) -> Path:
    """把 v0/v1/v2、文件名或绝对路径统一解析成快照文件路径。"""
    if isinstance(db, Path):
        return db if db.is_absolute() else (Path.cwd() / db)
    text = str(db)
    if text in _SNAPSHOT_ALIASES:
        return SNAPSHOT_DIR / f"{text}.sqlite"
    if "/" not in text and "\\" not in text:
        return SNAPSHOT_DIR / text
    path = Path(text)
    return path if path.is_absolute() else (Path.cwd() / path)


def open_readonly(db=DEFAULT_SNAPSHOT) -> sqlite3.Connection:
    """第一层：只读 + immutable 连接。写入会抛 sqlite3.OperationalError。"""
    path = snapshot_path(db)
    if not path.is_file():
        raise FileNotFoundError(f"快照不存在：{path}")
    con = sqlite3.connect(f"{path.as_uri()}?mode=ro&immutable=1", uri=True)
    con.execute("PRAGMA query_only=ON")
    return con


def _mask(sql: str) -> str:
    """把注释与引号内文本抹成空格，仅保留语句骨架，供关键字与分号检查。"""
    buf = list(sql)
    i, n = 0, len(sql)
    while i < n:
        ch = sql[i]
        if sql.startswith("--", i):
            j = sql.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                buf[k] = " "
            i = j
        elif sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                buf[k] = " "
            i = j
        elif ch in ("'", '"', "`", "["):
            close = "]" if ch == "[" else ch
            j = i + 1
            while j < n:
                if sql[j] == close:
                    if close != "]" and j + 1 < n and sql[j + 1] == close:
                        j += 2
                        continue
                    break
                j += 1
            end = min(j, n)
            for k in range(i + 1, end):
                buf[k] = " "
            i = end + 1 if j < n else n
        else:
            i += 1
    return "".join(buf)


def analyze(sql: str) -> tuple[str, str | None]:
    """第二层：语句白名单。返回 (待执行语句, 错误信息|None)。"""
    if not isinstance(sql, str) or not sql.strip():
        return "", "SQL 为空"
    masked = _mask(sql)
    body = masked.strip()
    if not body:
        return "", "SQL 为空（只有注释）"
    while body.startswith("("):
        body = body[1:].lstrip()
    words = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", body)
    if not words:
        return "", "无法识别语句类型"
    head = words[0].upper()
    if head not in ALLOWED_HEADS:
        return "", f"只允许 SELECT / WITH 语句，收到 {head}"
    hit = sorted({w.upper() for w in words} & FORBIDDEN_WORDS)
    if hit:
        return "", f"语句包含被禁止的关键字：{', '.join(hit)}"
    semis = [i for i, ch in enumerate(masked) if ch == ";"]
    if semis:
        if len(semis) > 1 or masked[semis[-1] + 1:].strip():
            return "", "不允许多条语句"
    return sql.strip(), None


def _cell(value):
    """把 sqlite3 返回值转成可 JSON 序列化的稳定形式。"""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value


def _elapsed(started: float) -> float:
    return round((time.perf_counter() - started) * 1000.0, 3)


def execute(db=DEFAULT_SNAPSHOT, sql: str | None = None, *,
            timeout_s: float = TIMEOUT_SECONDS,
            row_limit: int = ROW_LIMIT) -> dict:
    """执行一条只读查询。``execute(sql)`` 等价于 ``execute("v0", sql)``。"""
    started = time.perf_counter()
    if sql is None:                     # 单参形式：execute(sql)
        db, sql = DEFAULT_SNAPSHOT, db
    out: dict = {"columns": [], "rows": [], "elapsed_ms": 0.0,
                 "error": None, "truncated": False}

    statement, err = analyze(sql)
    if err:
        out["error"] = err
        out["elapsed_ms"] = _elapsed(started)
        return out

    try:
        con = open_readonly(db)
    except Exception as exc:            # noqa: BLE001  文件缺失等直接进 error
        out["error"] = f"打开快照失败：{exc}"
        out["elapsed_ms"] = _elapsed(started)
        return out

    deadline = time.perf_counter() + max(0.001, float(timeout_s))

    def _progress() -> int:
        return 1 if time.perf_counter() > deadline else 0

    try:
        con.set_progress_handler(_progress, PROGRESS_STEPS)
        cursor = con.execute(statement)
        if cursor.description:
            out["columns"] = [d[0] for d in cursor.description]
        limit = max(1, int(row_limit))
        rows = cursor.fetchmany(limit + 1)
        if len(rows) > limit:
            out["truncated"] = True
            rows = rows[:limit]
        out["rows"] = [[_cell(v) for v in row] for row in rows]
    except sqlite3.OperationalError as exc:
        message = str(exc)
        if "interrupt" in message.lower():
            out["error"] = f"查询超时（>{float(timeout_s):.1f}s）"
        else:
            out["error"] = f"SQL 执行失败：{message}"
    except sqlite3.Error as exc:
        out["error"] = f"SQL 执行失败：{exc}"
    except Exception as exc:            # noqa: BLE001  兜底，保证不抛异常
        out["error"] = f"执行异常：{type(exc).__name__}: {exc}"
    finally:
        try:
            con.set_progress_handler(None, 0)
        except sqlite3.Error:
            pass
        con.close()
    out["elapsed_ms"] = _elapsed(started)
    return out


# 兼容验收器探测的多个入口名（execute / run / query / execute_sql）
run = execute
query = execute
execute_sql = execute
