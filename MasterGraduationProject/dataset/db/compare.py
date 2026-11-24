"""结果规范化与比对。

规范化规则（compare 默认全部生效）
----------------------------------
1. 列顺序无关：按列名排序后再比对；
2. 数值统一 round 到 6 位小数（同时消掉 -0.0），整数与浮点按数值比较；
3. ``None`` 与 ``""`` 严格区分，``None`` 只等于 ``None``；
4. 日期/时间字符串统一成 ISO 形式（``2024/01/05`` → ``2024-01-05``，
   ``2024-05-15 06:00:00Z`` → ``2024-05-15T06:00:00``）；只统一表示形式，不丢弃时间分量；
5. 行序无关（按多重集比对），只有调用方显式传 ``ordered=True`` 才按行序比对。

``compare(a, b)`` 返回 ``{"equal": bool, "reason": str, "missing": [...], "extra": [...]}``：
``missing`` 是期望结果（a）里有、实际结果（b）里不足的行，``extra`` 反之；
同一行出现两次按两次计（多重集），不会被去重。
"""
from __future__ import annotations

import datetime as _dt
import re
from collections import Counter

ROUND_DIGITS = 6

_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_SLASH_DATE_RE = re.compile(r"^(\d{4})[/.](\d{1,2})[/.](\d{1,2})$")
_DATETIME_RE = re.compile(
    r"^(\d{4})-(\d{1,2})-(\d{1,2})[T ](\d{2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?"
    r"(?:Z|[+-]\d{2}:?\d{2})?$"
)


# ---------------------------------------------------------------------------
# 单值规范化
# ---------------------------------------------------------------------------
def _date_ok(y: int, m: int, d: int) -> bool:
    try:
        _dt.date(y, m, d)
    except ValueError:
        return False
    return True


def normalize_value(value):
    """把一个单元格规范化成可比较、可哈希的形式。"""
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return _num(value)
    if isinstance(value, float):
        return _num(value)
    if isinstance(value, str):
        return _text(value)
    if isinstance(value, (_dt.datetime, _dt.date)):
        return _iso(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return str(value)


def _num(value) -> float:
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        return number
    return round(number, ROUND_DIGITS) + 0.0


def _text(text: str) -> str:
    s = text.strip()
    if not s:
        return text
    m = _DATE_RE.fullmatch(s)
    if m and _date_ok(int(m.group(1)), int(m.group(2)), int(m.group(3))):
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = _SLASH_DATE_RE.fullmatch(s)
    if m and _date_ok(int(m.group(1)), int(m.group(2)), int(m.group(3))):
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = _DATETIME_RE.fullmatch(s)
    if m and _date_ok(int(m.group(1)), int(m.group(2)), int(m.group(3))):
        second = m.group(6) or "00"
        return (f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
                f"T{int(m.group(4)):02d}:{int(m.group(5)):02d}:{int(second):02d}")
    return text


def _iso(value) -> str:
    if isinstance(value, _dt.datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%S")
    return value.isoformat()


def _row_key(row) -> tuple:
    """跨类型的稳定排序键：None < 数值 < 字符串 < 其他。"""
    keys = []
    for value in row:
        if value is None:
            keys.append((0, ""))
        elif isinstance(value, (int, float)):
            keys.append((1, float(value)))
        elif isinstance(value, str):
            keys.append((2, value))
        else:
            keys.append((3, repr(value)))
    return tuple(keys)


# ---------------------------------------------------------------------------
# 结果拆解与规范化
# ---------------------------------------------------------------------------
def _dedupe(columns: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    out = []
    for name in columns:
        if name in seen:
            seen[name] += 1
            out.append(f"{name}#{seen[name]}")
        else:
            seen[name] = 1
            out.append(name)
    return out


def _as_table(result) -> tuple[list[str], list[list], str | None]:
    """把执行器结果 / dict 列表 / 元组列表 / 标量统一成 (columns, rows, error)。"""
    if isinstance(result, dict):
        error = result.get("error")
        if "columns" in result and "rows" in result:
            return (list(result["columns"]),
                    [list(row) for row in result["rows"]], error)
        if error:
            return [], [], error
        if "rows" in result:
            raw = [list(row) for row in result["rows"]]
            width = max((len(r) for r in raw), default=0)
            return [f"c{i}" for i in range(width)], raw, None
        columns = list(result.keys())
        return columns, [[result[c] for c in columns]], None
    if isinstance(result, (list, tuple)):
        items = list(result)
        if not items:
            return [], [], None
        if all(isinstance(x, dict) for x in items):
            columns: list[str] = []
            for item in items:
                for key in item:
                    if key not in columns:
                        columns.append(key)
            return columns, [[item.get(c) for c in columns] for item in items], None
        rows = [list(x) if isinstance(x, (list, tuple)) else [x] for x in items]
        width = max((len(r) for r in rows), default=0)
        return [f"c{i}" for i in range(width)], rows, None
    if result is None:
        return ["value"], [[None]], None
    return ["value"], [[result]], None


def normalize(result, *, ordered: bool = False) -> dict:
    """规范化任意结果：列按名排序、值规范化、行默认按内容排序。"""
    columns, raw_rows, error = _as_table(result)
    columns = _dedupe(columns)
    sorted_columns = sorted(columns)
    position = {name: i for i, name in enumerate(columns)}
    rows = []
    for raw in raw_rows:
        mapped = {name: (raw[position[name]] if position[name] < len(raw) else None)
                  for name in columns}
        rows.append([normalize_value(mapped[name]) for name in sorted_columns])
    if not ordered:
        rows.sort(key=_row_key)
    return {"columns": sorted_columns, "rows": rows, "error": error, "ordered": ordered}


def _row_dict(columns: list[str], row) -> dict:
    return {name: value for name, value in zip(columns, row)}


# ---------------------------------------------------------------------------
# 比对
# ---------------------------------------------------------------------------
def compare(a, b, *, ordered: bool = False) -> dict:
    """比对两个结果。默认行序无关、列序无关、数值 6 位容差。"""
    left = normalize(a, ordered=ordered)
    right = normalize(b, ordered=ordered)

    err_a, err_b = left["error"], right["error"]
    if err_a or err_b:
        if err_a and err_b:
            if err_a == err_b:
                return {"equal": True, "reason": "两侧报同样的错", "missing": [], "extra": []}
            return {"equal": False, "reason": "两侧报错不同", "missing": [], "extra": []}
        side = "a" if err_a else "b"
        return {"equal": False,
                "reason": f"仅 {side} 侧报错，另一侧是正常结果（含空结果）",
                "missing": [], "extra": []}

    if left["columns"] != right["columns"]:
        missing = [c for c in left["columns"] if c not in right["columns"]]
        extra = [c for c in right["columns"] if c not in left["columns"]]
        return {"equal": False,
                "reason": f"列集合不一致：缺少 {missing}，多出 {extra}",
                "missing": missing, "extra": extra}

    columns = left["columns"]
    rows_a, rows_b = left["rows"], right["rows"]
    missing: list[dict] = []
    extra: list[dict] = []

    if ordered:
        for i in range(max(len(rows_a), len(rows_b))):
            ra = rows_a[i] if i < len(rows_a) else None
            rb = rows_b[i] if i < len(rows_b) else None
            if ra == rb:
                continue
            if ra is not None:
                missing.append(_row_dict(columns, ra))
            if rb is not None:
                extra.append(_row_dict(columns, rb))
        if not missing and not extra:
            return {"equal": True, "reason": "完全一致（保序）", "missing": [], "extra": []}
        return {"equal": False,
                "reason": f"保序比对：{len(missing)} 行缺失/不同，{len(extra)} 行多出/不同",
                "missing": missing, "extra": extra}

    counter_a = Counter(tuple(row) for row in rows_a)
    counter_b = Counter(tuple(row) for row in rows_b)
    for row in sorted(counter_a, key=_row_key):
        for _ in range(max(0, counter_a[row] - counter_b.get(row, 0))):
            missing.append(_row_dict(columns, list(row)))
    for row in sorted(counter_b, key=_row_key):
        for _ in range(max(0, counter_b[row] - counter_a.get(row, 0))):
            extra.append(_row_dict(columns, list(row)))
    if not missing and not extra:
        return {"equal": True, "reason": "完全一致（多重集）", "missing": [], "extra": []}
    return {"equal": False,
            "reason": (f"多重集比对：{len(missing)} 行缺失，{len(extra)} 行多余"
                       f"（行数 {len(rows_a)} vs {len(rows_b)}）"),
            "missing": missing, "extra": extra}
