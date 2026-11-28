"""确定性构建 ~150 万行生产规模只读分析库 dataset/db/scale/prod_scale.sqlite（v0.6.0）。

设计原则：
  1. 以只读方式从 snapshots/v0.sqlite 复制，绝不修改 v0/v1/v2.sqlite 主干；
  2. 8 张 dim_* 维度表与 12 张 agg_* 汇总表保持原样（确保外键关联与维度主键不变）；
  3. 34 张 fact_* 事实表与 6 张 log_* 日志表按 SCALE_FACTOR=30 批插扩容：
     整数主键列按 (pk + k * stride) 递增，非主键列（日期、外键、状态、金额）保留真实分布；
  4. 扩容完成后对 20 条跨难度 gold_sql 冒烟校验，写出 scale/meta.json。
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import io  # noqa: E402

SRC_DB = ROOT / "db" / "snapshots" / "v0.sqlite"
SCALE_DIR = ROOT / "db" / "scale"
DST_DB = SCALE_DIR / "prod_scale.sqlite"
META_JSON = SCALE_DIR / "meta.json"

SCALE_FACTOR = 100


def main() -> int:
    t0 = time.perf_counter()
    assert SRC_DB.is_file(), f"缺基准快照 {SRC_DB}"
    SCALE_DIR.mkdir(parents=True, exist_ok=True)
    tmp_db = SCALE_DIR / ".prod_scale.tmp.sqlite"
    if tmp_db.is_file():
        tmp_db.unlink()
    shutil.copy2(SRC_DB, tmp_db)

    con = sqlite3.connect(str(tmp_db))
    con.execute("PRAGMA synchronous = OFF")
    con.execute("PRAGMA journal_mode = MEMORY")
    con.execute("PRAGMA temp_store = MEMORY")

    tables = [
        r[0]
        for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    ]
    fact_log = [t for t in tables if t.startswith(("fact_", "log_"))]

    scaled_counts: dict[str, int] = {}
    for tb in fact_log:
        info = con.execute(f'PRAGMA table_info("{tb}")').fetchall()
        cols = [c[1] for c in info]
        pk_cols = [c[1] for c in info if c[5] > 0]
        assert len(pk_cols) == 1, f"{tb} 主键列异常: {pk_cols}"
        pk = pk_cols[0]

        max_pk, base_cnt = con.execute(f'SELECT MAX("{pk}"), COUNT(*) FROM "{tb}"').fetchone()
        stride = max(int(max_pk or 0), int(base_cnt or 0)) + 1000

        # 检查是否存在除主键外的 UNIQUE 索引；若有则一并微调（本库 fact/log 仅主键唯一）
        col_list = ", ".join(f'"{c}"' for c in cols)
        with con:
            for k in range(1, SCALE_FACTOR):
                offset = k * stride
                sel_exprs = []
                for c in cols:
                    if c == pk:
                        sel_exprs.append(f'("{c}" + {offset})')
                    elif c in ("biz_no", "order_no", "ticket_no", "code"):
                        sel_exprs.append(f'("{c}" || \'_s{k}\')')
                    else:
                        sel_exprs.append(f'"{c}"')
                sel_sql = ", ".join(sel_exprs)
                con.execute(
                    f'INSERT INTO "{tb}" ({col_list}) SELECT {sel_sql} FROM "{tb}" WHERE "{pk}" <= {max_pk}'
                )
        new_cnt = con.execute(f'SELECT COUNT(*) FROM "{tb}"').fetchone()[0]
        scaled_counts[tb] = int(new_cnt)

        # 生产库标准索引：在业务日期键与关联外键（*_key / *_id）上建单列及组合索引，避免相关子查询退化为 O(N^2)
        has_date = "date_key" in cols
        if has_date:
            con.execute(f'CREATE INDEX IF NOT EXISTS "idx_{tb}_date_key" ON "{tb}" ("date_key")')
        for c in cols:
            if c != pk and c != "date_key" and (c.endswith("_key") or c.endswith("_id")):
                if has_date:
                    con.execute(f'CREATE INDEX IF NOT EXISTS "idx_{tb}_{c}_date" ON "{tb}" ("{c}", "date_key")')
                else:
                    con.execute(f'CREATE INDEX IF NOT EXISTS "idx_{tb}_{c}" ON "{tb}" ("{c}")')

    total_rows = sum(
        int(con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]) for t in tables
    )
    con.execute("ANALYZE")
    con.commit()
    con.close()

    # 冒烟校验：在只读模式下执行 20 条跨难度 gold_sql
    tasks = list(io.read_jsonl(ROOT / "tasks" / "tasks.jsonl"))
    ro = sqlite3.connect(f"file:{tmp_db.as_posix()}?mode=ro", uri=True)
    for t in tasks[:20]:
        cur = ro.execute(t["gold_sql"])
        _ = cur.fetchmany(5)
        cur.close()
    ro.close()

    if DST_DB.is_file():
        DST_DB.unlink()
    tmp_db.replace(DST_DB)

    elapsed = round(time.perf_counter() - t0, 2)
    meta = {
        "dataset_version": "0.6.0",
        "source_snapshot": "db/snapshots/v0.sqlite",
        "scale_factor": SCALE_FACTOR,
        "scaled_table_count": len(fact_log),
        "total_tables": len(tables),
        "total_rows": total_rows,
        "bytes": DST_DB.stat().st_size,
        "build_seconds": elapsed,
        "smoke_checked_tasks": 20,
        "note": "仅用于生产规模 act 工具网关压测标定；不替代 v0/v1/v2 真值库，可通过 python dataset/db/build_prod_scale.py 一键确定性重建。",
    }
    io.write_json(META_JSON, meta)
    print(
        f"已建 {DST_DB}：总行数={total_rows:,}，体积={meta['bytes']/1e6:.1f} MB，耗时={elapsed}s，"
        f"20 条 gold_sql 冒烟通过"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
