"""生成 dataset/db/MANIFEST.json：每个交付文件的 sha256 与行数。

用法：
  python dataset/db/manifest.py

MANIFEST 由脚本生成、不手写；build.py 结束时会自动调用一次。
MANIFEST.json 自身不入册（否则哈希自指）。
"""
from __future__ import annotations

import sys
from pathlib import Path

DB_DIR = Path(__file__).resolve().parent
ROOT = DB_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common import io  # noqa: E402

MANIFEST_JSON = DB_DIR / "MANIFEST.json"

# 文本交付物：登记行数；快照是二进制，行数记 null，另记字节数
TEXT_FILES = (
    "schema.sql",
    "gen_schema.py",
    "build.py",
    "manifest.py",
    "executor.py",
    "compare.py",
    "__init__.py",
    "tests/__init__.py",
    "tests/test_compare.py",
    "tests/test_executor.py",
    "snapshots/hashes.json",
)
BINARY_FILES = (
    "snapshots/v0.sqlite",
    "snapshots/v1.sqlite",
    "snapshots/v2.sqlite",
)


def _entry(path: Path, text: bool) -> dict:
    entry = {
        "sha256": io.sha256_file(path),
        "rows": (len(path.read_text(encoding="utf-8").splitlines()) if text else None),
        "bytes": path.stat().st_size,
    }
    return entry


def collect() -> dict:
    out: dict[str, dict] = {}
    for rel in TEXT_FILES:
        path = DB_DIR / rel
        if not path.is_file():
            raise FileNotFoundError(rel)
        out[rel] = _entry(path, True)
    for rel in BINARY_FILES:
        path = DB_DIR / rel
        if not path.is_file():
            raise FileNotFoundError(rel)
        out[rel] = _entry(path, False)
    return out


def write_manifest() -> dict:
    data = collect()
    io.write_json(MANIFEST_JSON, data)
    return data


def main() -> int:
    data = write_manifest()
    total_lines = sum(v["rows"] or 0 for v in data.values())
    print(f"[manifest] {MANIFEST_JSON.relative_to(ROOT).as_posix()} 已生成："
          f"{len(data)} 个文件 / 文本合计 {total_lines} 行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
