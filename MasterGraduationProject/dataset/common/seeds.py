"""唯一随机入口。

任何生成器都不得直接使用 random / np.random。统一调用 rng(stage, name)，
同一 (global_seed, stage, name) 必然产生同一序列，保证跨机器、跨进程可复现。
"""
from __future__ import annotations

import hashlib
import json
import os
import random
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_PARAMS = json.loads((_ROOT / "config" / "params.json").read_text(encoding="utf-8"))
GLOBAL_SEED: int = int(_PARAMS["global_seed"])


def derive(stage: str, name: str) -> int:
    """把 (stage, name) 稳定映射为 64 位整数种子。"""
    payload = f"{GLOBAL_SEED}|{stage}|{name}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def rng(stage: str, name: str) -> random.Random:
    return random.Random(derive(stage, name))


def shuffle(items, stage: str, name: str):
    """确定性洗牌，返回新列表，不修改入参。"""
    out = list(items)
    rng(stage, name).shuffle(out)
    return out


def choice_weighted(r: random.Random, table: dict) -> str:
    """按权重字典抽样，权重之和无需为 1。"""
    keys = list(table)
    weights = [table[k] for k in keys]
    total = sum(weights)
    x = r.random() * total
    acc = 0.0
    for k, w in zip(keys, weights):
        acc += w
        if x <= acc:
            return k
    return keys[-1]
