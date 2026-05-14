#!/usr/bin/env python3
"""
vLLM 本地推理脚本 —— 专为低显存 GPU（≤ 4GB）设计。

本脚本的所有参数默认值都针对 2GB 显存做过裁剪：
  - 默认上下文长度仅 2048（而非常见的 32K/128K）
  - 默认关闭 CUDA Graph（--enforce-eager），省去 graph 预分配的开销
  - GPU 利用率默认 0.85，给驱动/桌面留 15% 余量
  - 默认只允许 1 条并发请求

使用方式：
  python inference.py                          # 启动 API 服务
  python inference.py --model ./models/qwen2.5-0.5b-instruct
  python inference.py --port 8080 --max-model-len 1024
  python inference.py --chat                   # 交互式对话模式

如果你的模型已经放在 models/ 目录下，脚本会自动找第一个合法目录。
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# ---- 项目根目录（脚本所在目录）----
# PROJECT_ROOT = Path(__file__).resolve().parent
# MODELS_DIR = PROJECT_ROOT / "models"
MODELS_DIR = Path("/media/jgd/EA0AA0DD0AA0A851/models/Qwen3-0.6B")

# ============================================================================
# 推荐模型列表 —— 适合 2 GB 级别显存的推理模型
# ============================================================================
# 以下模型在启用 FP16 或 INT4 量化后大概率能塞进 2 GB VRAM。
# 排序按显存占用从低到高：
#
#   SmolLM2-135M-Instruct       FP16 ≈ 0.27 GB    流畅
#   SmolLM2-360M-Instruct       FP16 ≈ 0.72 GB    流畅
#   Qwen2.5-0.5B-Instruct       FP16 ≈ 1.0 GB     流畅（推荐入门）
#   TinyLlama-1.1B-Chat         FP16 ≈ 2.2 GB     需 INT4 / 减少上下文
#   Qwen2.5-1.5B-Instruct       FP16 ≈ 3.0 GB     需 INT4 + 512 ctx
#   Gemma-2-2B-it               INT4 ≈ 2.1 GB     需 --quantization awq
#
# HuggingFace 模型 ID → 本地路径映射（方便你下载）：
RECOMMENDED_MODELS: dict[str, str] = {
    "smollm2-135m": "HuggingFaceTB/SmolLM2-135M-Instruct",
    "smollm2-360m": "HuggingFaceTB/SmolLM2-360M-Instruct",
    "qwen2.5-0.5b": "Qwen/Qwen2.5-0.5B-Instruct",
    "tinyllama": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    "qwen2.5-1.5b": "Qwen/Qwen2.5-1.5B-Instruct",
}


def find_model_path(candidate: str) -> str:
    """
    把用户传入的 --model 解析为真实存在的目录路径。

    解析优先级：
    1. 如果是绝对路径且存在 → 直接返回
    2. 如果是相对路径，先在 models/ 下找，再到当前目录找
    3. 如果是推荐模型的简称（如 "qwen2.5-0.5b"） → 返回 models/<简称>
    4. 如果 models/ 下只有一个目录 → 自动使用它
    5. 以上都不满足 → 报错退出
    """
    # 1) 绝对路径
    if os.path.isabs(candidate) and Path(candidate).is_dir():
        return candidate

    # 2) 相对路径尝试 models/，再当前目录
    for base in (MODELS_DIR, PROJECT_ROOT):
        p = base / candidate
        if p.is_dir():
            return str(p.resolve())

    # 3) 推荐简称
    if candidate.lower() in RECOMMENDED_MODELS:
        expected = MODELS_DIR / candidate.lower()
        if expected.is_dir():
            return str(expected.resolve())
        print(
            f"[提示] 模型 '{candidate}' 对应 HuggingFace ID: {RECOMMENDED_MODELS[candidate.lower()]}\n"
            f"       请先把模型下载到: {expected}",
            file=sys.stderr,
        )
        sys.exit(1)

    # 4) models/ 下只有一个目录时自动选择
    existing = sorted(
        [d for d in MODELS_DIR.iterdir() if d.is_dir()]
    )
    if len(existing) == 1:
        print(f"[自动检测] 仅有一个模型目录，使用: {existing[0].name}")
        return str(existing[0].resolve())

    # 5) 无可用的模型
    print(
        f"错误: 找不到模型路径 '{candidate}'。\n"
        f"请将模型放入 {MODELS_DIR}/ 目录下，或通过 --model 指定路径。\n"
        f"推荐的小模型: {list(RECOMMENDED_MODELS.keys())}",
        file=sys.stderr,
    )
    sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
    """
    构建命令行参数解析器。

    每一项参数都有默认值，它们是一个"对 2 GB 显存友好的基准线"。
    如果你换了更大的卡，可以把 --gpu-memory-utilization / --max-model-len
    调大以获得更好的体验。
    """
    parser = argparse.ArgumentParser(
        description="vLLM 本地推理脚本（低显存优化版）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
模型推荐（2 GB VRAM 安全）:
  smollm2-135m       {RECOMMENDED_MODELS['smollm2-135m']}
  smollm2-360m       {RECOMMENDED_MODELS['smollm2-360m']}
  qwen2.5-0.5b       {RECOMMENDED_MODELS['qwen2.5-0.5b']}
  tinyllama           {RECOMMENDED_MODELS['tinyllama']}
  qwen2.5-1.5b        {RECOMMENDED_MODELS['qwen2.5-1.5b']}

示例:
  python inference.py                              # 自动检测模型并启动 API
  python inference.py --model qwen2.5-0.5b         # 使用推荐简称
  python inference.py --chat                        # 命令行交互式对话
  python inference.py --max-model-len 1024          # 进一步缩短上下文以省显存
        """,
    )

    # ======================== 模型相关 ========================
    parser.add_argument(
        "--model",
        type=str,
        default="",
        help=(
            "模型路径。可以是绝对路径、相对路径（先在 models/ 下找）、"
            "或推荐模型的简称（如 qwen2.5-0.5b）。留空则自动搜索 models/ 目录。"
        ),
    )
    parser.add_argument(
        "--dtype",
        type=str,
        default="auto",
        choices=["auto", "float16", "bfloat16", "float32"],
        help=(
            "推理精度。auto 会根据模型 config.json 自动选择。"
            "2 GB 显存强烈建议 float16 或 bfloat16，不要用 float32。"
        ),
    )
    parser.add_argument(
        "--quantization",
        type=str,
        default=None,
        choices=[None, "awq", "gptq", "squeezellm", "fp8", "bitsandbytes"],
        help=(
            "量化方法。如果你的模型是 AWQ/GPTQ 等量化版本，必须指定此项。"
            "非量化模型请保持默认 None。"
        ),
    )

    # ======================== 显存控制（关键！）==================
    parser.add_argument(
        "--gpu-memory-utilization",
        type=float,
        default=0.85,
        help=(
            "GPU 显存利用率上限（0~1）。"
            "2 GB 显存建议 0.80~0.90；"
            "若同时需要桌面渲染可降到 0.75。"
        ),
    )
    parser.add_argument(
        "--max-model-len",
        type=int,
        default=2048,
        help=(
            "模型最大上下文长度（token 数），默认 2048。"
            "这是 KV cache 占用的关键参数——值越小，显存占用越低。"
            "2 GB 显存建议 512~2048，不要用模型的 native max_seq_len。"
        ),
    )
    parser.add_argument(
        "--enforce-eager",
        action="store_true",
        default=True,
        help=(
            "强制使用 eager 模式（关闭 CUDA Graph）。"
            "CUDA Graph 会额外预分配显存来缓存计算图，"
            "小显存场景必须关闭。默认启用。"
        ),
    )
    parser.add_argument(
        "--no-enforce-eager",
        action="store_true",
        dest="disable_enforce_eager",
        help="关闭 --enforce-eager（即允许 CUDA Graph），仅大显存卡推荐。",
    )

    # ======================== 并发控制 ========================
    parser.add_argument(
        "--max-num-seqs",
        type=int,
        default=1,
        help=(
            "最大并发序列数。低显存只能设 1，"
            "设为 >1 时需要更大的 KV cache 空间。"
        ),
    )
    parser.add_argument(
        "--max-num-batched-tokens",
        type=int,
        default=2048,
        help="单批次最大 token 数，不要超过 --max-model-len。",
    )

    # ======================== 服务配置 ========================
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="API 服务监听地址（默认 0.0.0.0）。",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="API 服务监听端口（默认 8000）。",
    )
    parser.add_argument(
        "--chat",
        action="store_true",
        default=False,
        help="不启动 HTTP 服务，而是进入命令行交互式对话模式。",
    )

    # ======================== 其他 ========================
    parser.add_argument(
        "--trust-remote-code",
        action="store_true",
        default=True,
        help="信任并执行模型仓库中的自定义代码。某些模型（如 Qwen）需要此项。",
    )
    parser.add_argument(
        "--no-trust-remote-code",
        action="store_true",
        dest="disable_trust_remote_code",
        help="禁止执行模型仓库中的自定义代码。",
    )

    return parser


def run_api_server(args: argparse.Namespace) -> None:
    """
    启动 vLLM OpenAI-compatible API 服务。

    使用 vLLM 的 AsyncLLMEngine 拉起一个兼容 OpenAI /v1/chat/completions
    接口的 HTTP 服务。客户端可以用 openai 库或任意 HTTP 客户端调用。
    """
    from vllm.entrypoints.openai.api_server import (
        run_server,
        AsyncEngineArgs,
    )

    model_path = find_model_path(args.model) if args.model else find_model_path("")

    # 构建 vLLM 引擎参数
    engine_args = AsyncEngineArgs(
        model=model_path,
        dtype=args.dtype,
        quantization=args.quantization,
        gpu_memory_utilization=args.gpu_memory_utilization,
        max_model_len=args.max_model_len,
        enforce_eager=not args.disable_enforce_eager,
        max_num_seqs=args.max_num_seqs,
        max_num_batched_tokens=args.max_num_batched_tokens,
        trust_remote_code=not args.disable_trust_remote_code,
    )

    print(f"模型路径:     {model_path}")
    print(f"模型最大长度: {args.max_model_len} tokens")
    print(f"显存利用率:   {args.gpu_memory_utilization}")
    print(f"量化方式:     {args.quantization or '无'}")
    print(f"Eager 模式:   {not args.disable_enforce_eager}")
    print(f"服务地址:     http://{args.host}:{args.port}")
    print("-" * 50)

    run_server(engine_args, host=args.host, port=args.port)


def run_chat_mode(args: argparse.Namespace) -> None:
    """
    命令行交互式对话模式。

    不启动 HTTP 服务，直接在终端里和模型对话。
    每轮对话会携带完整历史记录（受 --max-model-len 约束）。
    """
    from vllm import LLM, SamplingParams

    model_path = find_model_path(args.model) if args.model else find_model_path("")

    print(f"正在加载模型: {model_path} ...")
    print(f"（2 GB 显存加载可能需要 10~30 秒，请耐心等待）")

    # ---- 初始化 vLLM 引擎 ----
    # LLM 构造函数的参数与 AsyncEngineArgs 含义一致。
    # 注意：
    #   - gpu_memory_utilization 控制 KV cache 和权重总共能占用的显存比例
    #   - max_model_len 直接决定 KV cache 的预分配大小
    #   - enforce_eager=True 关闭 CUDA Graph，省显存但推理速度会略慢
    llm = LLM(
        model=model_path,
        dtype=args.dtype,
        quantization=args.quantization,
        gpu_memory_utilization=args.gpu_memory_utilization,
        max_model_len=args.max_model_len,
        enforce_eager=not args.disable_enforce_eager,
        max_num_seqs=args.max_num_seqs,
        max_num_batched_tokens=args.max_num_batched_tokens,
        trust_remote_code=not args.disable_trust_remote_code,
    )

    # ---- 采样参数 ----
    # temperature=0.7 适合日常对话；需要严谨答案时可调低至 0.1~0.3
    sampling_params = SamplingParams(
        temperature=0.7,
        top_p=0.9,
        max_tokens=min(512, args.max_model_len),
        repetition_penalty=1.05,
    )

    print("\n模型加载完成！输入 'exit' 或 'quit' 退出，输入 'clear' 清空对话历史。\n")

    # ---- 对话循环 ----
    conversation: list[dict[str, str]] = []

    while True:
        try:
            user_input = input("You > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("再见！")
            break
        if user_input.lower() == "clear":
            conversation.clear()
            print("[对话历史已清空]")
            continue

        # 将用户消息追加到历史
        conversation.append({"role": "user", "content": user_input})

        # 构建 vLLM prompt（使用聊天模板格式）
        # vLLM 的 chat 接口接收 OpenAI 格式的 messages 列表
        # 这里使用 apply_chat_template 将对话历史转为模型可识别的格式
        tokenizer = llm.get_tokenizer()
        prompt = tokenizer.apply_chat_template(
            conversation,
            tokenize=False,
            add_generation_prompt=True,
        )

        # 执行推理
        outputs = llm.generate(
            [prompt],
            sampling_params=sampling_params,
        )

        # 提取生成的文本
        assistant_reply = outputs[0].outputs[0].text

        print(f"\nAssistant > {assistant_reply}\n")

        # 将助手回复追加到历史（下一次请求时一并携带）
        conversation.append({"role": "assistant", "content": assistant_reply})


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # 确保 models 目录存在
    MODELS_DIR.mkdir(exist_ok=True)

    if args.chat:
        run_chat_mode(args)
    else:
        run_api_server(args)


if __name__ == "__main__":
    main()
