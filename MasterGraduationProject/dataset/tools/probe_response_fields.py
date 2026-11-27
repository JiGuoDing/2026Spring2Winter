"""探测 chat/completions 响应里思考（reasoning）相关字段的真实结构。

目的：确认服务端把 reasoning 文本/token 数放在哪个字段，以便标定脚本正确统计
"思考 token 占比"，而不是像现在这样恒为 0。

只用极小请求（max_tokens=32），对正在跑的标定批次影响可忽略。
不打印密钥；输出只保留字段名、类型、长度与 token 计数。
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def call(base: str, key: str, payload: dict) -> dict:
    req = urllib.request.Request(
        base + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 **({"Authorization": f"Bearer {key}"} if key else {})})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


def walk(obj, prefix="", depth=0):
    """打印所有键的路径、类型与（字符串）长度。"""
    if depth > 3:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            if isinstance(v, str):
                print(f"  {path:55s} str(len={len(v)})")
            elif isinstance(v, (dict, list)):
                print(f"  {path:55s} {type(v).__name__}(len={len(v)})")
                walk(v, path, depth + 1)
            else:
                print(f"  {path:55s} {type(v).__name__} = {v}")


def main() -> int:
    env = parse_env(ROOT / ".env")
    base = env["LLM_BASE_URL"].rstrip("/")
    key = env.get("LLM_API_KEY", "")
    model = env.get("LLM_MODEL_SMALL", "")

    payload = {
        "model": model, "temperature": 0, "max_tokens": 32,
        "reasoning_effort": "xhigh",
        "messages": [{"role": "user", "content": "9 的平方根是多少？只回答数字。"}],
    }
    data = call(base, key, payload)
    print("=== 响应结构（全部字段路径）===")
    walk(data)
    print("\n=== usage 明细 ===")
    print(json.dumps(data.get("usage"), ensure_ascii=False, indent=2))
    msg = (data.get("choices") or [{}])[0].get("message") or {}
    print("\n=== message 各字段长度 ===")
    for k, v in msg.items():
        print(f"  {k}: {type(v).__name__} len={len(v) if hasattr(v, '__len__') else '-'}")
    print("\n=== 结论线索 ===")
    hit = [k for k in json.dumps(data) .split('"') if "reason" in k.lower()]
    print("  含 'reason' 的键名片段:", sorted(set(hit))[:20])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
