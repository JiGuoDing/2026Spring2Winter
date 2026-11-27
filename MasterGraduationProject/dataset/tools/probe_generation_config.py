"""探测端点支持的生成参数：max_tokens / reasoning_effort / thinking 开关。

目的：确认服务端接受哪种"高推理强度"写法，以及放大 max_tokens 后单次生成的真实时长，
避免把 5 小时的标定变成 50 小时。

不打印密钥；每个变体只发一次最小请求。
"""
from __future__ import annotations

import argparse
import json
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
    scheme, rest = url.split("://", 1)
    return f"{scheme}://{rest.split('/', 1)[0]}/…"


def call(base: str, key: str, payload: dict, timeout: float) -> dict:
    req = urllib.request.Request(
        base + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 **({"Authorization": f"Bearer {key}"} if key else {})})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        return {"ok": True, "t": time.perf_counter() - t0, "data": data}
    except urllib.error.HTTPError as e:
        body = e.read()[:300].decode("utf-8", "replace")
        return {"ok": False, "t": time.perf_counter() - t0, "err": f"HTTP {e.code}: {body}"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "t": time.perf_counter() - t0,
                "err": f"{type(e).__name__}: {str(e)[:160]}"}


def summarize(res: dict) -> str:
    if not res["ok"]:
        return f"FAIL {res['t']:.1f}s  {res['err']}"
    d = res["data"]
    ch = (d.get("choices") or [{}])[0]
    msg = ch.get("message") or {}
    usage = d.get("usage") or {}
    has_reason = "reasoning_content" in msg or "reasoning" in msg
    reason_len = len(msg.get("reasoning_content") or msg.get("reasoning") or "")
    return (f"OK {res['t']:.1f}s  finish={ch.get('finish_reason')}  "
            f"prompt={usage.get('prompt_tokens')} completion={usage.get('completion_tokens')}  "
            f"content_len={len(msg.get('content') or '')} reasoning={has_reason}({reason_len})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env-file", default=str(ROOT / ".env"))
    ap.add_argument("--timeout", type=float, default=300.0)
    args = ap.parse_args()

    env = parse_env(Path(args.env_file))
    base = env.get("LLM_BASE_URL", "").rstrip("/")
    key = env.get("LLM_API_KEY", "")
    model = env.get("LLM_MODEL_SMALL", "")
    print(f"endpoint {mask(base)}  model {model}")

    question = "用一句话说明：为什么缓存需要版本校验？"
    variants = [
        ("baseline max_tokens=64", {"max_tokens": 64}),
        ("reasoning_effort=xhigh", {"max_tokens": 64, "reasoning_effort": "xhigh"}),
        ("chat_template_kwargs.enable_thinking", {"max_tokens": 64,
                                                  "chat_template_kwargs": {"enable_thinking": True}}),
        ("enable_thinking=True(top)", {"max_tokens": 64, "enable_thinking": True}),
        ("max_tokens=2048 (看是否自然停)", {"max_tokens": 2048}),
    ]
    for name, extra in variants:
        payload = {"model": model, "temperature": 0, "messages": [
            {"role": "user", "content": question}], **extra}
        res = call(base, key, payload, args.timeout)
        print(f"[{name}] {summarize(res)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
