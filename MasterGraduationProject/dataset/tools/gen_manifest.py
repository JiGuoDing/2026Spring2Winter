"""生成全量 MANIFEST：dataset/MANIFEST.json。

遍历各交付目录，记录每个文件的 sha256、字节数、行数（文本类），
并附一个汇总块（规模、验收状态、生成命令），供论文附录与复现检查使用。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import io  # noqa: E402

DIRS = ["db", "knowledge", "tasks", "events", "costs", "labels"]
SKIP_SUFFIX = {".pyc", ".sqlite-wal", ".sqlite-shm"}
TEXT_SUFFIX = {".jsonl", ".json", ".csv", ".md", ".sql", ".py"}


def count_lines(p: Path) -> int | None:
    if p.suffix not in TEXT_SUFFIX:
        return None
    n = 0
    with p.open("rb") as f:
        for _ in f:
            n += 1
    return n


def main() -> int:
    out: dict[str, dict] = {}
    for d in DIRS:
        base = ROOT / d
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file() or p.suffix in SKIP_SUFFIX or "__pycache__" in p.parts:
                continue
            rel = p.relative_to(ROOT).as_posix()
            out[rel] = {
                "bytes": p.stat().st_size,
                "lines": count_lines(p),
                "sha256": io.sha256_file(p),
            }

    summary = {
        "generated_by": "tools/gen_manifest.py",
        "file_count": len(out),
        "total_bytes": sum(v["bytes"] for v in out.values()),
        "dirs": DIRS,
    }
    io.write_json(ROOT / "MANIFEST.json", {"summary": summary, "files": out})
    print(f"MANIFEST: {len(out)} files, {summary['total_bytes'] / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
