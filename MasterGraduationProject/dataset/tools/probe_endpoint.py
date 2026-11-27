"""单次探针：验证 LLM 端点可达性与单次往返耗时。

用途：标定全量跑之前先判断端点是否活着、延迟量级是否正常。
不打印密钥，只打印脱敏后的 scheme+host 与模型名。

用法：
  python dataset/tools/probe_endpoint.py
  python dataset/tools/probe_endpoint.py --timeout 120 --model-profile large
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
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


def mask(url: str) -> str:
    if "://" not in url:
        return "<非法>"
    scheme, rest = url.split("://", 1)
    return f"{scheme}://{rest.split('/', 1)[0]}/…"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env-file", default=str(ROOT / ".env"))
    ap.add_argument("--timeout", type=float, default=90.0)
    ap.add_argument("--model-profile", choices=["small", "large"], default="small")
    args = ap.parse_args()

    env = parse_env(Path(args.env_file))
    base = env.get("LLM_BASE_URL", "").rstrip("/")
    key = env.get("LLM_API_KEY", "")
    model = env.get("LLM_MODEL_SMALL" if args.model_profile == "small" else "LLM_MODEL_LARGE", "")
    if not base or not model:
        print("[ERROR] .env 缺 LLM_BASE_URL 或对应模型名")
        return 2

    url = base + "/chat/completions"
    payload = {"model": model, "temperature": 0, "max_tokens": 8,
               "messages": [{"role": "user", "content": "只回复两个字：收到"}]}
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 **({"Authorization": f"Bearer {key}"} if key else {})})
    print(f"endpoint : {mask(base)}")
    print(f"model    : {model}")
    print(f"timeout  : {args.timeout:.0f}s")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"[FAIL] HTTP {e.code}: {e.read()[:300].decode('utf-8','replace')}")
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] {time.perf_counter() - t0:.1f}s {type(e).__name__}: {str(e)[:200]}")
        return 1
    dt = time.perf_counter() - t0
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    print(f"[OK] 往返 {dt:.2f}s | 返回模型 {data.get('model')} | usage {data.get('usage')}")
    print(f"内容：{(content or '')[:40]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
