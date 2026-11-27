"""回溯展示一条完整标定记录：请求 → 规划 → 检索 → 执行 → 回答 → 汇总。

进度文件只存了 plan_text / resp_text / rag.doc_ids / 各段耗时；本工具按同一套确定性逻辑
重建当时的检索上下文与执行 SQL，拼成一条可读的完整 trace。

用法：
  python dataset/tools/show_calibration_record.py                # 展示第一条
  python dataset/tools/show_calibration_record.py --req-id r000005
  python dataset/tools/show_calibration_record.py --index last
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from common import io  # noqa: E402

import run_model_calibration as cal  # noqa: E402

PROGRESS = ROOT / "embeddings" / "calibration" / "requests_progress.jsonl"


def hr(title: str) -> None:
    print("\n" + "=" * 78)
    print(f"  {title}")
    print("=" * 78)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--req-id", default=None)
    ap.add_argument("--index", default="first", help="first / last / 从 0 开始的序号")
    ap.add_argument("--context-chars", type=int, default=1400)
    args = ap.parse_args()

    rows = [json.loads(l) for l in PROGRESS.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not rows:
        print("进度文件为空")
        return 1
    if args.req_id:
        rec = next(r for r in rows if r["req_id"] == args.req_id)
    elif args.index == "last":
        rec = rows[-1]
    elif args.index == "first":
        rec = rows[0]
    else:
        rec = rows[int(args.index)]

    inputs = cal.load_inputs(limit=0)
    item = next(it for it in inputs["items"] if it["req_id"] == rec["req_id"])
    req = item["request"]
    task = inputs["tasks"].get(item["task_id"])
    item["task"] = task          # run_requests 里才会挂上，回溯时需手动补
    # 用同一套确定性检索重建上下文
    lookup = cal.EmbeddingLookup(cal.NPZ)
    docs = cal.DocsIndex(cal.DOCS_JSONL)
    rag = cal.stage_rag(lookup, docs, item)

    hr("① 请求（用户侧）")
    print(f"req_id      : {rec['req_id']}   task_id: {rec['task_id']}   snapshot: {rec['snapshot']}")
    print(f"domain/perm : {req.get('domain')} / {req.get('permission')}")
    print(f"到达时刻    : {req.get('timestamp')}   对象角色: {req.get('obj_types')}")
    print(f"query       : {req['query_text']}")

    hr("② 规划（plan 阶段，模型输出）")
    print(f"耗时 {rec['t_plan_ms']:.0f} ms | prompt {rec['plan']['prompt_tokens']} / "
          f"completion {rec['plan']['completion_tokens']} token | finish={rec.get('plan_finish')}")
    print("-" * 78)
    print(rec["plan_text"].strip() or "<空>")

    hr("③ 检索（rag 阶段，本地确定性）")
    print(f"耗时 {rec['t_rag_ms']:.2f} ms（其中检索 {rec['t_rag_retrieve_ms']:.2f} ms）| "
          f"向量维度 {rec['rag']['vec_dim']}")
    print(f"命中文档 {len(rag['doc_ids'])} 篇：{rag['doc_ids']}")
    ctx = rag["context"]
    print(f"上下文长度 {len(ctx)} 字符，预览前 {args.context_chars}：")
    print("-" * 78)
    print(ctx[:args.context_chars] + ("\n…（截断）" if len(ctx) > args.context_chars else ""))

    hr("④ 执行（act 阶段 + 执行结果注入）")
    print(f"耗时 {rec['t_act_ms']:.2f} ms | 口径：{rec['act_source']}")
    if task:
        print("执行的 gold SQL：")
        print("-" * 78)
        print(task["gold_sql"].strip())
        sys.path.insert(0, str(ROOT / "db"))
        import executor  # noqa: PLC0415
        block = cal.stage_exec_result(item, executor)
        print(f"\n注入给 resp 的执行结果（{len(block)} 字符）：")
        print("-" * 78)
        print(block)

    hr("⑤ 回答（resp 阶段，模型输出）")
    print(f"耗时 {rec['t_resp_ms']:.0f} ms | prompt {rec['resp']['prompt_tokens']} / "
          f"completion {rec['resp']['completion_tokens']} token | "
          f"finish={rec.get('resp_finish')} | 触顶={rec.get('resp_truncated')}")
    print("-" * 78)
    print(rec["resp_text"].strip() or "<空>")

    hr("⑥ 汇总")
    print(f"端到端 {rec['t_total_ms']:.0f} ms = plan {rec['t_plan_ms']:.0f} + "
          f"rag {rec['t_rag_ms']:.2f} + act {rec['t_act_ms']:.2f} + resp {rec['t_resp_ms']:.0f}")
    print(f"token 合计 {rec['token_cost']}（plan+resp 的 prompt+completion）")
    print(f"plan 触顶={rec.get('plan_truncated')}  resp 触顶={rec.get('resp_truncated')}")
    if task:
        print(f"真值（gold 执行结果）: {str(task['truth']['value'])[:200]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
