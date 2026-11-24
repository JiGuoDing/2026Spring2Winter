"""由 dataset/contracts/tables.json 生成 dataset/db/schema.sql。

用法：
  python dataset/db/gen_schema.py

约定：
1. 表名、字段名、字段顺序、字段类型、主键、非空约束与 tables.json 一一对应，不增不减；
2. 只生成目录里的 60 张业务表。v2 才出现的 2 张扩展表不属于目录，由 build.py 在
   结构变更阶段创建，避免 DDL 与目录不一致；
3. 不写外键、索引、默认值、CHECK，保证快照文件可逐字节重建；
4. 标识符统一用双引号包裹，除此之外不加任何修饰。
"""
from __future__ import annotations

import sys
from pathlib import Path

DB_DIR = Path(__file__).resolve().parent
ROOT = DB_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common import io  # noqa: E402

TABLES_JSON = ROOT / "contracts" / "tables.json"
SCHEMA_SQL = DB_DIR / "schema.sql"

# 目录中只允许出现 SQLite 原生类型，出现别的类型即视为契约被改坏。
ALLOWED_TYPES = ("INTEGER", "REAL", "TEXT")


def load_tables() -> list[dict]:
    """读取 60 表目录（唯一真源）。"""
    payload = io.read_json(TABLES_JSON)
    tables = payload["tables"]
    assert len(tables) == payload["table_count"], "table_count 与 tables 长度不一致"
    return tables


def q(name: str) -> str:
    """SQLite 标识符转义。"""
    return '"' + name.replace('"', '""') + '"'


def render_ddl(tables: list[dict]) -> str:
    """把表目录渲染成可直接 executescript 的 DDL 文本。"""
    total_fields = sum(len(t["fields"]) for t in tables)
    lines = [
        "-- 由 dataset/db/gen_schema.py 从 dataset/contracts/tables.json 生成，请勿手改。",
        f"-- 表数 {len(tables)}，字段数 {total_fields}。",
        "-- 字段名、顺序、类型、主键、非空约束与目录一一对应；类型仅用 INTEGER / REAL / TEXT。",
        "",
    ]
    for t in tables:
        head = f"-- {t.get('table_id', '')} {t['name']}"
        if "kind" in t:
            head += f" kind={t['kind']}"
        if "rows" in t:
            head += f" rows={t['rows']}"
        lines.append(head)
        lines.append(f"CREATE TABLE {q(t['name'])} (")
        parts = []
        for f in t["fields"]:
            ftype = f["type"].upper()
            if ftype not in ALLOWED_TYPES:
                raise ValueError(f"{t['name']}.{f['name']} 类型 {ftype} 不在允许集合内")
            null_clause = "" if f.get("nullable", True) else " NOT NULL"
            parts.append(f"  {q(f['name'])} {ftype}{null_clause}")
        pks = [f["name"] for f in t["fields"] if f.get("pk")]
        if pks:
            parts.append("  PRIMARY KEY (" + ", ".join(q(p) for p in pks) + ")")
        lines.append(",\n".join(parts))
        lines.append(");")
        lines.append("")
    return "\n".join(lines)


def write_schema(tables: list[dict] | None = None) -> Path:
    tables = load_tables() if tables is None else tables
    SCHEMA_SQL.write_text(render_ddl(tables), encoding="utf-8", newline="\n")
    return SCHEMA_SQL


def main() -> int:
    tables = load_tables()
    # 目录自检：60 表 × 20 字段，且主键唯一
    for t in tables:
        assert len(t["fields"]) == 20, f"{t['name']} 字段数不是 20"
        assert sum(1 for f in t["fields"] if f.get("pk")) == 1, f"{t['name']} 主键不唯一"
    path = write_schema(tables)
    fields = sum(len(t["fields"]) for t in tables)
    print(f"[gen_schema] {path.relative_to(ROOT).as_posix()} 已生成："
          f"{len(tables)} 表 / {fields} 字段")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
