"""从 dataset/.env 读取凭据并驱动模型标定脚本。

为什么需要它：标定脚本只认环境变量，而交互式 shell 里临时设的变量不会传给新的进程。
本脚本把 .env 里的键值注入子进程环境，键值不落盘、不回显、不写入任何数据集产物。

用法：
  python dataset/tools/run_calibration_from_env.py --dry-run     # 先校验环境与文件
  python dataset/tools/run_calibration_from_env.py --limit 5     # 试跑 5 条（不写回）
  python dataset/tools/run_calibration_from_env.py               # 全量，两个模型各一轮
  python dataset/tools/run_calibration_from_env.py --alias small # 只跑一个档案

跑完后请删除 dataset/.env。
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CALIB = ROOT / "tools" / "run_model_calibration.py"
ALIASES = {"small": "local-qwen3-8-27b", "large": "api-large-placeholder"}


def parse_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise SystemExit(f"[ERROR] 找不到 {path}。请复制 dataset/.env.example 为 dataset/.env 后填写。")
    out: dict[str, str] = {}
    # utf-8-sig：兼容 Windows 记事本 / PowerShell Out-File 写入的 BOM
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip().lstrip("\ufeff")
        val = val.strip().strip('"').strip("'")
        if key:
            out[key] = val
    return out


def mask_url(url: str) -> str:
    """只保留 scheme+host，避免把内部路径/query 打出来。"""
    if not url:
        return "<空>"
    if "://" not in url:
        return "<非法>"
    scheme, rest = url.split("://", 1)
    host = rest.split("/", 1)[0]
    return f"{scheme}://{host}/…"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env-file", default=str(ROOT / ".env"))
    ap.add_argument("--dry-run", action="store_true", help="只校验，不调用接口、不写回")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--alias", choices=["small", "large", "both"], default="both")
    ap.add_argument("--branch-sample", type=int, default=None,
                    help="分支配对抽样对数（默认 30；0=不测）")
    ap.add_argument("--resume", action="store_true",
                    help="从 embeddings/calibration/requests_progress.jsonl 断点续跑")
    args = ap.parse_args()

    env = parse_env(Path(args.env_file))
    base = env.get("LLM_BASE_URL", "").strip()
    key = env.get("LLM_API_KEY", "").strip()
    models = {"small": env.get("LLM_MODEL_SMALL", "").strip(),
              "large": env.get("LLM_MODEL_LARGE", "").strip()}

    if not base:
        raise SystemExit("[ERROR] .env 缺 LLM_BASE_URL")
    is_local = any(h in base for h in ("127.0.0.1", "localhost", "::1"))
    if not is_local and not key:
        raise SystemExit("[ERROR] 目标不是 localhost，必须提供 LLM_API_KEY")

    chosen = ["small", "large"] if args.alias == "both" else [args.alias]
    runnable = [(a, models[a]) for a in chosen if models[a]]
    missing = [a for a in chosen if not models[a]]

    print("=" * 66)
    print(f"基址      : {mask_url(base)}")
    print(f"密钥      : {'已提供（不回显）' if key else '空（本地端点）'}")
    print(f"档案映射  : " + ", ".join(f"{a}→{m}" for a, m in runnable) if runnable else "档案映射  : <无>")
    if missing:
        print(f"未配置    : {missing}（对应成本行将保持 mock=pending，属实说明）")
    print(f"模式      : {'dry-run' if args.dry_run else '真实调用'}"
          + (f"，limit={args.limit}" if args.limit else ""))
    est = 0
    n = args.limit or 300
    for a, _ in runnable:
        est += n * 2 + (0 if args.dry_run else 60)
    if est:
        print(f"调用量估算: 约 {est} 次模型调用（plan+resp 各一次/请求，分支配对另计）")
    print("=" * 66)
    if not runnable:
        raise SystemExit("[ERROR] .env 里没有可用的 LLM_MODEL_SMALL / LLM_MODEL_LARGE")
    if est > 2000:
        print("[提醒] 调用量较大，请确认额度与预算；可先 --limit 5 试跑。")

    fails = []
    for alias, model in runnable:
        child_env = dict(os.environ)
        child_env.update({"LLM_BASE_URL": base, "LLM_API_KEY": key, "LLM_MODEL": model})
        cmd = [sys.executable, str(CALIB), "--model-alias", ALIASES[alias]]
        if args.dry_run:
            cmd.append("--dry-run")
        if args.limit:
            cmd += ["--limit", str(args.limit), "--no-write-back"]
        if args.branch_sample is not None:
            cmd += ["--branch-sample", str(args.branch_sample)]
        if args.resume:
            cmd.append("--resume")
        print(f"\n>>> {alias}: {model}")
        r = subprocess.run(cmd, env=child_env, cwd=str(ROOT.parent))
        if r.returncode != 0:
            fails.append((alias, model, r.returncode))

    print("\n" + "=" * 66)
    if fails:
        print("失败：", fails)
        return 1
    print("全部完成。请检查 events/real_calibration_300.csv 与 costs/path_costs.csv。")
    print("安全提示：现在删除 dataset/.env，并按需轮换 key。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
