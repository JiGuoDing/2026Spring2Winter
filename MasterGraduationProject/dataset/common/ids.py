"""唯一 ID 入口。

规则：所有表、字段、文档、块、请求、更新事件的标识只能由本模块生成或校验，
其他模块禁止手拼 ID 字符串。ID 变更必须先改本文件并记入 contracts/CHANGELOG.md。
"""
from __future__ import annotations

import re

# ---- 表与字段 -------------------------------------------------------------
def table_id(i: int) -> str:
    """t01..t60"""
    if not 1 <= i <= 99:
        raise ValueError(i)
    return f"t{i:02d}"


def field_id(tbl: str, idx: int) -> str:
    """fld_t01_01"""
    if not re.fullmatch(r"t\d{2}", tbl):
        raise ValueError(tbl)
    return f"fld_{tbl}_{idx:02d}"


# ---- 知识文档 -------------------------------------------------------------
def whitepaper_id(i: int) -> str:
    return f"wp_{i:03d}"


def metric_id(i: int) -> str:
    return f"metric_{i:03d}"


def tool_id(i: int) -> str:
    return f"tool_{i:03d}"


def plan_id(i: int) -> str:
    return f"plan_{i:02d}"


def note_id(i: int) -> str:
    return f"note_{i:03d}"


# ---- 块、请求、更新、配对 -------------------------------------------------
def block_id(doc_id: str, p: int) -> str:
    """证据块 ID，跨版本稳定：doc_id#p01"""
    if not DOC_ID_RE.fullmatch(doc_id):
        raise ValueError(f"bad doc_id: {doc_id}")
    return f"{doc_id}#p{p:02d}"


def req_id(seq: int) -> str:
    """r000001"""
    if seq < 1:
        raise ValueError(seq)
    return f"r{seq:06d}"


def upd_id(seq: int) -> str:
    """u0001"""
    if seq < 1:
        raise ValueError(seq)
    return f"u{seq:04d}"


def branch_pair_id(seq: int) -> str:
    """b00001"""
    return f"b{seq:05d}"


def task_id(seq: int) -> str:
    """q001"""
    return f"q{seq:03d}"


# ---- 校验 -----------------------------------------------------------------
DOC_ID_RE = re.compile(
    r"(fld_t\d{2}_\d{2}|wp_\d{3}|metric_\d{3}|tool_\d{3}|plan_\d{2}|note_\d{3})"
)
DOC_ID_FULL_RE = re.compile(
    r"(fld_t\d{2}_\d{2}|wp_\d{3}|metric_\d{3}|tool_\d{3}|plan_\d{2}|note_\d{3})"
)
BLOCK_ID_RE = re.compile(
    r"(fld_t\d{2}_\d{2}|wp_\d{3}|metric_\d{3}|tool_\d{3}|plan_\d{2}|note_\d{3})#p\d{2}"
)


def is_valid_doc_id(s: str) -> bool:
    return bool(DOC_ID_FULL_RE.fullmatch(s))


def is_valid_block_id(s: str) -> bool:
    return bool(BLOCK_ID_RE.fullmatch(s))


CLUSTER_ID_RE = re.compile(r"cls_[a-z0-9_]+")


def is_valid_cluster_id(s: str) -> bool:
    return bool(CLUSTER_ID_RE.fullmatch(s))


def doc_type_of(doc_id: str) -> str:
    """由 ID 前缀反推文档类型，供生成器与校验器共用。"""
    if doc_id.startswith("fld_t"):
        return "field"
    for prefix, kind in (
        ("wp_", "whitepaper"),
        ("metric_", "metric"),
        ("tool_", "tool"),
        ("plan_", "plan"),
        ("note_", "note"),
    ):
        if doc_id.startswith(prefix):
            return kind
    raise ValueError(f"unknown doc_id: {doc_id}")
