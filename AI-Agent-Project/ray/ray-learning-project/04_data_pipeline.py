"""
================================================================================
  Ray 学习项目 · 第四课：完整数据处理流水线
================================================================================

  场景设定
  ────────
  模拟一个实时广告点击日志处理系统：
  1. 日志生成   → 模拟多个广告投放渠道实时产生点击日志
  2. 日志清洗   → 过滤无效数据，标准化格式
  3. 实时聚合   → 按广告主维度聚合点击量、花费、转化
  4. 异常检测   → 检测点击量突增（可能的刷量行为）
  5. 结果存储   → 写入本地文件（生产环境可替换为数据库）
  6. 监控面板   → Actor 维护的实时统计仪表盘

  🎯 本课重点
  ──────────
  • 综合运用前 3 课的所有知识（remote task, Actor, 资源管理）
  • 理解 Ray 相比 Flink 在"灵活批处理 + 动态调度"场景中的优势
  • 体验 Ray 如何用普通 Python 代码实现"类似流处理"的效果

  📖 与 Flink 实现对比
  ───────────────────
  如果用 Flink 实现同样逻辑：
  - Source:     Kafka / 自定义 SourceFunction
  - Map:        MapFunction (清洗)
  - KeyBy:      keyBy(AdvertiserId)
  - Window:     TumblingWindow(10s) / SlidingWindow
  - Process:    ProcessWindowFunction (聚合 + 异常检测)
  - Sink:       JDBC Sink / File Sink

  Ray 的实现方式：
  - 所有逻辑都是普通 Python 对象和函数
  - 不需要窗口机制（用显式的定时批处理代替）
  - 不需要序列化框架（cloudpickle 自动处理所有 Python 对象）
  - 可以根据数据特征动态调整处理逻辑
  - 任意阶段都可以插入 "人机交互"（如人工审核异常）
"""

import ray
import time
import random
import json
import os
import uuid
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from datetime import datetime


# ============================================================================
# 数据模型定义
# ============================================================================

@dataclass
class ClickEvent:
    """广告点击事件 —— 流水线中的基本数据单元。

    --- Flink 类比 ---
    这就是 DataStream 中的 POJO / Row，在 Flink 中你需要定义序列化器 (TypeInfo)。
    Ray 中 dataclass 配合 cloudpickle 自动序列化，零配置。
    """
    event_id: str           # 事件唯一 ID
    advertiser_id: str      # 广告主 ID —— Flink keyBy 的 key
    campaign_id: str        # 广告活动 ID
    user_id: str            # 点击用户 ID
    cost: float             # 单次点击成本（CPC）
    click_time: float       # 点击时间戳
    channel: str            # 渠道：google / facebook / tiktok / wechat
    ip_address: str         # 用户 IP
    is_valid: bool = True   # 是否为有效点击（清洗后标记）


@dataclass
class AggregatedStats:
    """按广告主的聚合统计结果。

    --- Flink 类比 ---
    相当于 WindowFunction 的输出类型。
    """
    advertiser_id: str
    window_start: float
    window_end: float
    total_clicks: int = 0
    total_cost: float = 0.0
    unique_users: int = 0
    channels: Dict[str, int] = field(default_factory=dict)
    avg_cost_per_click: float = 0.0


# ============================================================================
# 第一部分：日志生成器 —— 模拟数据源
# ============================================================================

print("=" * 70)
print("  实时广告点击日志处理流水线")
print("=" * 70)

ray.init(address="auto", ignore_reinit_error=True)


class LogGenerator:
    """
    本地数据生成器（在主进程中运行）。
    模拟多个渠道持续产生广告点击日志。

    --- Flink 类比 ---
    类似 Flink 的 SourceFunction<ClickEvent>，在 run() 中循环产生数据，
    通过 SourceContext.collect() 输出到 DataStream。
    在 Ray 中，我们直接将数据 batch 放入 Object Store。
    """

    ADVERTISERS = ["ad_001", "ad_002", "ad_003", "ad_004", "ad_005"]
    CHANNELS = ["google", "facebook", "tiktok", "wechat"]

    @staticmethod
    def generate_batch(batch_size: int = 50) -> List[ClickEvent]:
        """生成一批模拟点击事件。"""
        events = []
        now = time.time()
        for _ in range(batch_size):
            advertiser = random.choice(LogGenerator.ADVERTISERS)
            campaign = f"{advertiser}_camp_{random.randint(1,10)}"
            channel = random.choice(LogGenerator.CHANNELS)

            # 模拟 CPC 价格区间（根据渠道不同）
            base_cost = {
                "google": 2.0, "facebook": 1.5,
                "tiktok": 1.0, "wechat": 0.8,
            }

            event = ClickEvent(
                event_id=str(uuid.uuid4())[:8],
                advertiser_id=advertiser,
                campaign_id=campaign,
                user_id=f"user_{random.randint(1, 1000)}",
                cost=round(random.uniform(0.5, 3.0) * base_cost.get(channel, 1.0), 2),
                click_time=now - random.uniform(0, 5),  # 过去 5 秒内
                channel=channel,
                ip_address=f"192.168.{random.randint(1,255)}.{random.randint(1,255)}",
                is_valid=True,
            )
            events.append(event)
        return events


# 快速验证
sample = LogGenerator.generate_batch(3)
print(f"\n📌 生成 {len(sample)} 条样本日志:")
for e in sample:
    print(f"   {e}")


# ============================================================================
# 第二部分：日志清洗 —— 分布式过滤与标准化
# ============================================================================

# --- Flink 类比 ---
# 类似 Flink 的 DataStream.map(new CleanFunction()) + DataStream.filter(...)
# 但在 Ray 中，清洗逻辑是一个无状态的 remote task，天然并行。

@ray.remote
def clean_and_validate(batch: List[ClickEvent]) -> List[ClickEvent]:
    """
    清洗和验证日志批次。

    执行以下操作：
    1. 过滤明显无效的点击（IP 地址异常、cost 异常）
    2. 标准化字段（如统一渠道名称大小写）
    3. 计算事件延迟（当前时间 - click_time）

    --- Flink 类比 ---
    相当于 Flink 中的 MapFunction + FilterFunction 的组合，
    但 Ray 版本需要手动管理 batch 边界（Flink 自动处理每条记录）。
    """
    cleaned = []
    now = time.time()

    for event in batch:
        # 规则1：过滤掉 cost 为负或 0 的异常数据
        if event.cost <= 0:
            event.is_valid = False
            continue

        # 规则2：过滤掉事件时间过于久远的（> 60 秒前）
        if now - event.click_time > 60:
            event.is_valid = False
            continue

        # 规则3：标准化渠道名称为小写
        event.channel = event.channel.lower().strip()

        # 规则4：过滤明显的刷量 IP（模拟：简单规则检测）
        if event.ip_address.startswith("10."):  # 内网 IP，不可能是真实用户
            event.is_valid = False
            continue

        # 规则5：同一 advertiser + user 在一秒内重复点击 → 标记为可疑
        # （这里简化处理，生产环境需要查状态）
        event.is_valid = True
        cleaned.append(event)

    return cleaned


# ============================================================================
# 第三部分：按广告主聚合 —— 类似 Flink KeyBy + Window
# ============================================================================

# --- Flink 类比 ---
# Flink 中聚合是通过 keyBy + window 自动实现的。
# Ray 中没有内置 window，但你拥有了"手写聚合逻辑"的灵活性。
# 下面的实现就像是你自己在实现一个 mini 的 WindowOperator。

@ray.remote
def aggregate_by_advertiser(batch: List[ClickEvent]) -> List[AggregatedStats]:
    """
    按广告主维度聚合一批点击事件。

    --- Flink 类比 ---
    相当于 Flink 中 keyBy(advertiser_id).window(TumblingWindow).aggregate()
    的区别：
    - Flink 窗口边界由事件时间/处理时间自动划分
    - Ray 窗口边界由你传入的 batch 数据隐式决定（更原始但更可控）
    """
    # 按广告主分组（这就是 keyBy 的逻辑）
    groups: Dict[str, List[ClickEvent]] = defaultdict(list)
    for event in batch:
        if event.is_valid:
            groups[event.advertiser_id].append(event)

    stats_list = []
    now = time.time()
    window_start = now - 5.0  # 模拟一个 5 秒的时间窗口
    window_end = now

    for advertiser_id, events in groups.items():
        unique_users = set(e.user_id for e in events)
        channels = defaultdict(int)
        total_cost = 0.0

        for e in events:
            channels[e.channel] += 1
            total_cost += e.cost

        stats = AggregatedStats(
            advertiser_id=advertiser_id,
            window_start=window_start,
            window_end=window_end,
            total_clicks=len(events),
            total_cost=round(total_cost, 2),
            unique_users=len(unique_users),
            channels=dict(channels),
            avg_cost_per_click=round(total_cost / len(events), 4) if events else 0.0,
        )
        stats_list.append(stats)

    return stats_list


# ============================================================================
# 第四部分：异常检测 Actor —— 有状态的刷量检测
# ============================================================================

# --- Flink 类比 ---
# Flink 中实现异常检测通常用 KeyedProcessFunction + TimerService：
#   维护每个广告主的近期点击量，定时清理过期状态。
# Ray 中用 Actor 实现：Actor 内部维护一个滑动窗口计数器，
# 新数据到达时更新计数、检测异常。

@ray.remote
class AnomalyDetector:
    """
    异常检测器 Actor —— 检测每个广告主的点击量异常。

    内部维护：
    - 滑动窗口计数器（过去 10 秒内每个广告主的点击数）
    - 历史基线（每个广告主的历史平均点击率）
    - 告警阈值

    --- Flink 类比 ---
    类似 Flink 中的 KeyedProcessFunction<AdvertiserId, ClickEvent, Alert>，
    但 Actor 的状态更灵活（任意 Python 对象），且告警可以直接发送到通知系统
    （如 Slack Webhook），不需要额外的 sink。
    """

    def __init__(self, alert_threshold: float = 3.0):
        """
        alert_threshold: 异常倍数阈值。如果当前窗口点击量 > 基线 × threshold → 告警
        """
        self.alert_threshold = alert_threshold
        # 滑动窗口计数器: {advertiser_id: [(timestamp, count), ...]}
        self.window_counts: Dict[str, List[Tuple[float, int]]] = defaultdict(list)
        # 历史基线: {advertiser_id: avg_clicks_per_second}
        self.baselines: Dict[str, float] = {}
        self.alert_history: List[Dict] = []  # 告警记录
        self.total_processed: int = 0

    def update_and_detect(
        self, stats_list: List[AggregatedStats]
    ) -> List[Dict]:
        """
        更新统计数据并检测异常。

        参数:
            stats_list: 按广告主聚合的统计结果

        返回:
            Alert 列表: [{advertiser_id, severity, current, baseline, ...}]

        --- Flink 类比 ---
        类似 ProcessFunction.processElement()，但处理的是聚合后的批量数据，
        而不是逐条处理原始事件。
        """
        now = time.time()
        alerts = []
        self.total_processed += len(stats_list)

        for stats in stats_list:
            aid = stats.advertiser_id
            clicks = stats.total_clicks

            # 1) 更新滑动窗口（保留过去 10 秒的记录）
            self.window_counts[aid].append((now, clicks))
            # 清理 10 秒以上的旧记录
            cutoff = now - 10.0
            self.window_counts[aid] = [
                (t, c) for t, c in self.window_counts[aid] if t > cutoff
            ]

            # 2) 计算当前窗口的总点击量
            current_window_total = sum(c for _, c in self.window_counts[aid])

            # 3) 更新历史基线（指数移动平均）
            if aid in self.baselines:
                alpha = 0.3  # 平滑因子
                self.baselines[aid] = (
                    alpha * clicks + (1 - alpha) * self.baselines[aid]
                )
            else:
                self.baselines[aid] = float(clicks)

            # 4) 异常判断
            baseline = self.baselines[aid]
            if baseline > 0 and clicks > baseline * self.alert_threshold:
                severity = "🔴 HIGH" if clicks > baseline * 5 else "🟡 MEDIUM"

                alert = {
                    "timestamp": now,
                    "advertiser_id": aid,
                    "severity": severity,
                    "current_clicks": clicks,
                    "baseline_clicks": round(baseline, 2),
                    "ratio": round(clicks / baseline, 2),
                    "window_total": current_window_total,
                }
                alerts.append(alert)
                self.alert_history.append(alert)

                # 在生产环境中，这里可以直接调用 Slack/钉钉 Webhook
                # requests.post(WEBHOOK_URL, json=alert)

        return alerts

    def get_status(self) -> Dict:
        """获取检测器的运行状态。"""
        return {
            "total_processed_batches": self.total_processed,
            "tracked_advertisers": len(self.window_counts),
            "total_alerts": len(self.alert_history),
            "recent_alerts": self.alert_history[-5:],  # 最近 5 条告警
            "current_baselines": {
                aid: round(b, 2) for aid, b in self.baselines.items()
            },
        }

    def get_advertiser_detail(self, advertiser_id: str) -> Dict:
        """获取特定广告主的详细信息。"""
        return {
            "advertiser_id": advertiser_id,
            "window_counts": self.window_counts.get(advertiser_id, []),
            "baseline": round(self.baselines.get(advertiser_id, 0), 2),
        }

    def update_threshold(self, new_threshold: float) -> str:
        """动态更新告警阈值（不需要重启！）。"""
        old = self.alert_threshold
        self.alert_threshold = new_threshold
        return f"阈值已从 {old} 更新为 {new_threshold}"


# ============================================================================
# 第五部分：结果存储 —— 模拟写入外部系统
# ============================================================================

# --- Flink 类比 ---
# 类似 Flink 的 SinkFunction / JDBC Sink。
# Ray 中可以随意使用 Python 的任何 IO 库（open(), boto3, psycopg2, requests...）
# 没有任何限制，因为 remote task 内是一个完整的 Python 进程。

@ray.remote
class ResultWriter:
    """
    结果写入器 Actor —— 负责将聚合结果持久化。

    使用 Actor 而非 remote task 的原因：
    - 维护文件句柄（避免每次打开/关闭文件）
    - 保证写入顺序（Actor 串行处理写入请求）
    - 可以定时 flush（类似 Flink sink 的批量提交）

    --- Flink 类比 ---
    相当于 Flink 的 RichSinkFunction，open() 打开连接，invoke() 写入数据，
    close() 关闭连接。
    """

    def __init__(self, output_dir: str = "./ray_pipeline_output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.stats_file = open(f"{output_dir}/stats.jsonl", "a", encoding="utf-8")
        self.alerts_file = open(f"{output_dir}/alerts.jsonl", "a", encoding="utf-8")
        self.total_writes = 0
        self.total_size_bytes = 0
        print(f"  📁 结果写入器已就绪，输出目录: {output_dir}")

    def write_stats(self, stats_list: List[AggregatedStats]) -> int:
        """写入聚合统计（追加模式，JSONL 格式）。"""
        written = 0
        for stats in stats_list:
            line = json.dumps(asdict(stats), ensure_ascii=False) + "\n"
            self.stats_file.write(line)
            self.total_size_bytes += len(line.encode("utf-8"))
            written += 1
        self.total_writes += written
        self.stats_file.flush()  # 确保数据持久化
        return written

    def write_alerts(self, alerts: List[Dict]) -> int:
        """写入告警记录。"""
        written = 0
        for alert in alerts:
            alert["written_at"] = time.time()
            line = json.dumps(alert, ensure_ascii=False) + "\n"
            self.alerts_file.write(line)
            self.total_size_bytes += len(line.encode("utf-8"))
            written += 1
        self.total_writes += written
        self.alerts_file.flush()
        return written

    def close(self) -> Dict:
        """关闭文件句柄，返回写入统计。"""
        self.stats_file.close()
        self.alerts_file.close()
        return {
            "total_writes": self.total_writes,
            "total_size_kb": round(self.total_size_bytes / 1024, 2),
        }

    def get_write_count(self) -> int:
        return self.total_writes


# ============================================================================
# 第六部分：监控面板 Actor —— 实时仪表盘
# ============================================================================

@ray.remote
class Dashboard:
    """
    监控面板 Actor —— 聚合全局运行的实时指标。

    --- Flink 类比 ---
    Flink 中这需要通过 Metrics Reporter（如 Prometheus PushGateway）收集指标。
    Ray 中可以通过 Actor 直接收集和查询，对开发和调试更友好。
    """

    def __init__(self):
        self.start_time = time.time()
        self.total_events_processed = 0
        self.total_batches = 0
        self.pipeline_latencies: List[float] = []  # 每批次的端到端延迟

    def report_batch(
        self, batch_size: int, latency: float, valid_count: int
    ) -> None:
        """记录一个批次的处理完成。"""
        self.total_events_processed += batch_size
        self.total_batches += 1
        self.pipeline_latencies.append(latency)

    def get_dashboard(self) -> Dict:
        """获取当前仪表盘数据。"""
        uptime = time.time() - self.start_time
        # 只保留最近 50 个延迟数据
        recent_latencies = self.pipeline_latencies[-50:]

        if recent_latencies:
            avg_latency = sum(recent_latencies) / len(recent_latencies)
            p99_latency = sorted(recent_latencies)[int(len(recent_latencies) * 0.99)] \
                if len(recent_latencies) > 1 else recent_latencies[0]
        else:
            avg_latency = 0
            p99_latency = 0

        return {
            "uptime_seconds": round(uptime, 1),
            "total_events": self.total_events_processed,
            "total_batches": self.total_batches,
            "throughput_eps": round(
                self.total_events_processed / uptime, 1
            ) if uptime > 0 else 0,
            "avg_latency_ms": round(avg_latency * 1000, 1),
            "p99_latency_ms": round(p99_latency * 1000, 1),
        }


# ============================================================================
# 第七部分：主流水线 —— 组合所有组件
# ============================================================================

print("\n" + "=" * 70)
print("  主流水线启动")
print("=" * 70)


def run_pipeline(
    num_batches: int = 10,     # 模拟处理的批次数
    batch_size: int = 50,      # 每批日志条数
    parallel_cleaners: int = 4, # 并行清洗任务数
):
    """
    主流水线函数 —— 协调所有组件。

    流水线结构:
    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐
    │ LogGenerator │ →  │ clean_...()  │ →  │ aggregate_() │ →  │ Result   │
    │ (本地)       │    │ (remote task)│    │ (remote task)│    │ Writer   │
    └──────────────┘    └──────────────┘    └──────────────┘    │ (Actor)  │
           │                   │                   │            └──────────┘
           │             ┌─────┴─────┐      ┌──────┴──────┐          │
           │             │ 4 个并行   │      │ Anomaly     │          │
           │             │ 清洗任务   │      │ Detector    │          │
           │             └───────────┘      │ (Actor)     │          │
           │                                └─────────────┘          │
           │         ┌───────────┐               │                   │
           └────────→│ Dashboard │←──────────────┘                   │
                     │ (Actor)   │←──────────────────────────────────┘
                     └───────────┘
    """
    # 初始化 Actor
    dashboard = Dashboard.remote()
    detector = AnomalyDetector.remote(alert_threshold=3.0)
    writer = ResultWriter.remote(output_dir="./ray_pipeline_output")

    generator = LogGenerator()

    print(f"\n流水线配置:")
    print(f"  批次数: {num_batches}")
    print(f"  每批大小: {batch_size} 条日志")
    print(f"  并行清洗任务: {parallel_cleaners}")
    print(f"  预计总数据量: ~{num_batches * batch_size} 条日志\n")

    all_alerts = []

    for batch_idx in range(num_batches):
        batch_start = time.time()

        # 阶段 1: 生成日志（本地执行）
        raw_batch = generator.generate_batch(batch_size)

        # 阶段 2: 分布式清洗
        # 将批次切分为 sub-batch，分发给多个清洗任务并行处理
        sub_size = max(1, len(raw_batch) // parallel_cleaners)
        sub_batches = [
            raw_batch[i:i + sub_size]
            for i in range(0, len(raw_batch), sub_size)
        ]
        # 并行清洗
        clean_refs = [clean_and_validate.remote(sb) for sb in sub_batches]
        cleaned_results = ray.get(clean_refs)  # 等待所有子批次清洗完成
        # 合并清洗结果
        all_cleaned = []
        for sub in cleaned_results:
            all_cleaned.extend(sub)

        # 阶段 3: 按广告主聚合
        stats_ref = aggregate_by_advertiser.remote(all_cleaned)
        stats = ray.get(stats_ref)

        # 阶段 4: 异常检测
        alerts_ref = detector.update_and_detect.remote(stats)
        alerts = ray.get(alerts_ref)
        if alerts:
            all_alerts.extend(alerts)

        # 阶段 5: 结果存储（异步：不等写入完成就进入下一轮）
        writer.write_stats.remote(stats)
        if alerts:
            writer.write_alerts.remote(alerts)

        # 阶段 6: 更新仪表盘
        batch_latency = time.time() - batch_start
        dashboard.report_batch.remote(
            len(raw_batch), batch_latency, len(all_cleaned)
        )

        # 打印进度
        progress = (batch_idx + 1) / num_batches * 100
        bar = "█" * int(progress / 5) + "░" * (20 - int(progress / 5))
        print(f"  [{bar}] 批次 {batch_idx+1:3d}/{num_batches}  "
              f"原始={len(raw_batch)}, 有效={len(all_cleaned)}, "
              f"告警={len(alerts)}, 延迟={batch_latency*1000:.0f}ms")

    # 最终报告
    print(f"\n{'='*70}")
    print(f"  流水线执行完成！")
    print(f"{'='*70}")

    dashboard_data = ray.get(dashboard.get_dashboard.remote())
    detector_status = ray.get(detector.get_status.remote())
    write_stats = ray.get(writer.close.remote())

    print(f"\n📊 仪表盘:")
    for key, value in dashboard_data.items():
        print(f"   {key}: {value}")

    print(f"\n🚨 异常检测器:")
    print(f"   处理批次: {detector_status['total_processed_batches']}")
    print(f"   追踪广告主数: {detector_status['tracked_advertisers']}")
    print(f"   总告警数: {detector_status['total_alerts']}")
    if detector_status['recent_alerts']:
        print(f"   最近告警:")
        for alert in detector_status['recent_alerts']:
            print(f"     {alert['severity']} {alert['advertiser_id']}: "
                  f"当前={alert['current_clicks']}, "
                  f"基线={alert['baseline_clicks']}, "
                  f"比率={alert['ratio']}x")

    print(f"\n📁 写入统计:")
    print(f"   写入条数: {write_stats['total_writes']}")
    print(f"   写入大小: {write_stats['total_size_kb']} KB")

    # 输出文件位置
    print(f"\n📂 输出文件位于: ./ray_pipeline_output/")
    print(f"   stats.jsonl  - 聚合统计结果")
    print(f"   alerts.jsonl - 异常告警记录")

    return {
        "dashboard": dashboard_data,
        "alerts": all_alerts,
        "writes": write_stats,
    }


# 运行流水线
pipeline_result = run_pipeline(
    num_batches=10,
    batch_size=50,
    parallel_cleaners=4,
)


# ============================================================================
# 第八部分：查看输出文件
# ============================================================================

print("\n" + "=" * 70)
print("  查看输出文件内容")
print("=" * 70)

output_dir = "./ray_pipeline_output"

if os.path.exists(f"{output_dir}/stats.jsonl"):
    print(f"\n📄 stats.jsonl 内容样例（前 5 行）:")
    with open(f"{output_dir}/stats.jsonl", "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= 5:
                break
            data = json.loads(line)
            print(f"   {json.dumps(data, ensure_ascii=False)}")
    total_lines = sum(1 for _ in open(f"{output_dir}/stats.jsonl", "r", encoding="utf-8"))
    print(f"   ... 共 {total_lines} 行")

if os.path.exists(f"{output_dir}/alerts.jsonl"):
    print(f"\n📄 alerts.jsonl 内容:")
    with open(f"{output_dir}/alerts.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            alert = json.loads(line)
            print(f"   {json.dumps(alert, ensure_ascii=False)}")

# ============================================================================
# 收尾
# ============================================================================

ray.shutdown()
print(f"\n✅ Ray 已关闭")
print(f"\n💡 提示: 查看完整输出文件请使用:")
print(f"   cat ray_pipeline_output/stats.jsonl")
print(f"   cat ray_pipeline_output/alerts.jsonl")


# ============================================================================
# 第九部分：Ray vs Flink 综合对比总结
# ============================================================================

print("\n" + "=" * 70)
print("  终章：Ray vs Flink —— 何时选谁？")
print("=" * 70)

print("""
  ┌─────────────────────────────────────────────────────────────────────┐
  │                      Ray vs Flink 决策矩阵                          │
  ├──────────────────────────────┬──────────────────┬───────────────────┤
  │ 维度                         │ Ray              │ Flink             │
  ├──────────────────────────────┼──────────────────┼───────────────────┤
  │ 核心范式                     │ 通用分布式计算    │ 有状态流处理       │
  │ 数据处理模式                 │ 批处理 / RPC     │ 流处理 (事件驱动)  │
  │ 状态管理                     │ 手动 (Actor 属性)│ 自动 (Checkpoint)  │
  │ 容错保证                     │ 最多一次/重试    │ Exactly-Once      │
  │ 延迟                         │ 毫秒~秒 (任务级)│ 毫秒级 (事件级)   │
  │ 吞吐                         │ 中高 (取决于任务)│ 高 (流式管道)     │
  │ Window / 时间语义            │ 需自建           │ 内置 Watermark    │
  │ SQL / Table API              │ ❌               │ ✅                │
  │ Python 生态                  │ ✅ 原生一等公民   │ ⚠️  PyFlink      │
  │ 动态 DAG                     │ ✅ 核心优势       │ ❌ 编译时确定     │
  │ GPU / ML 集成               │ ✅ 原生支持       │ ⚠️  需外部服务    │
  │ 交互式开发                   │ ✅ Jupyter 直连   │ ❌ 需提交 JAR     │
  │ 资源粒度                     │ 灵活 (小数 CPU)   │ 固定 (Slot)       │
  │ 运维复杂度                   │ 中等             │ 较高              │
  └──────────────────────────────┴──────────────────┴───────────────────┘

  📌 选 Ray 的场景：
  • ML 训练/推理、超参搜索、模型服务
  • 需要动态任务调度、灵活并行（如批处理 ETL、数据处理探索）
  • 需要 Python 生态深度集成（NumPy/Pandas/PyTorch）
  • 实时性要求不高（秒级延迟可接受）的聚合计算
  • 快速原型验证 → 再决定是否迁移到 Flink

  📌 选 Flink 的场景：
  • 严苛的 Exactly-Once 语义需求（金融交易、计费系统）
  • 真正的实时流处理（毫秒级事件级延迟）
  • 复杂的 Event Time / Watermark / Window 语义
  • 大规模 SQL 驱动的流分析（Flink SQL）
  • 已有 Java 团队和基础设施

  📌 两者协作的场景（Ray + Flink）：
  • Flink 处理实时流 → 输出到 Kafka → Ray 消费做 ML 推理
  • Ray 训练的模型 → 部署到 Flink 作业中做在线预测
  • Flink 做实时 ETL → Ray 做离线分析/报表生成
""")


# ============================================================================
# 📝 综合面试问题
# ============================================================================

"""
Q17: 如果让你设计一个系统，什么时候选 Ray 而不是 Flink？
────────────────────────────────────────────────────
A: 核心判断标准是"状态的复杂度"和"延迟要求"：
   1. 如果需要 Exactly-Once + 事件时间语义 + 毫秒级延迟 → Flink
   2. 如果计算模式是离散的（任务有开始和结束）、需要动态 DAG → Ray
   3. 如果需要大量使用 Python ML 库（PyTorch/TF）→ Ray
   4. 如果团队熟悉 Python 但不熟悉 Java/JVM 生态 → Ray
   5. 如果是不确定的数据探索和分析阶段 → Ray（快速试错）

Q18: 上面的流水线中，为什么异常检测用 Actor 而不用 remote task？
─────────────────────────────────────────────────────────
A: 异常检测需要维护"状态"：每个广告主的滑动窗口计数和历史基线。
   如果用 remote task，每次调用都从零开始，无法跨批次累积状态。
   Actor 保持进程常驻，self.window_counts 在多次调用之间保持，
   这是实现有状态处理的关键。这也解释了为什么 Flink 的 KeyedProcessFunction
   能维护状态 —— 它本身就是一个"逻辑 Actor"。

Q19: 在 Ray 中如何实现类似 Flink Watermark 的效果？
─────────────────────────────────────────────────
A: 没有内置 Watermark，但有几种替代方案：
   1. 在 Actor 内部维护每个 source 的 event time 进度，手动判断是否触发计算
   2. 使用 ray.wait() 的超时机制实现"延迟触发"
   3. 使用 Cron/scheduler 定时触发批处理（类似本流水线的方式）
   这些方案都不如 Flink 的 Watermark 机制精确，但对于许多场景（容许秒级延迟
   的聚合分析）已经足够。

Q20: 如何在 Ray 上实现故障恢复？和 Flink 的 Checkpoint 有什么不同？
─────────────────────────────────────────────────────────────
A: Flink Checkpoint 是框架级别的自动快照：状态、偏移量、算子位置全部一致地保存。
   Ray 提供多层次的容错机制：
   1. 任务级: max_retries 控制重试次数，默认重试系统级故障（worker 崩溃、节点故障）；
      设置 retry_exceptions=True 可对应用异常也重试。Ray 还支持基于血缘（lineage）
      的对象重建 —— 当任务结果丢失时自动重新执行上游任务。
   2. Actor 级: max_restarts 控制自动重启次数（默认 0 不重启，-1 无限重启）；
      重启时 __init__ 重新执行，但内存状态丢失。
   3. 应用级: 定期将 Actor 状态序列化到外部存储（类似手动 checkpoint）
   4. Ray Serve / Ray Train 等高层库提供了更完善的容错封装
   总体来说：Flink 的容错是"开箱即用"的（checkpoint 覆盖状态+位点），
   Ray 的容错更灵活但需要按需配置 —— 这也是两者设计哲学的差异：
   Flink 是"框架负责容错"，Ray 是"给你工具，你自己决定如何容错"。

Q21: Ray 的 Object Store 内存溢出会发生什么？如何避免？
─────────────────────────────────────────────────────
A: 当 Object Store 内存满时，Ray 会将对象溢出到磁盘（/tmp/ray/session_xxx/），
   这会导致后续 ray.get() 显著变慢（磁盘 IO 替代内存访问）。
   避免方法：
   1. 让 ObjectRef 的 Python 引用自然超出作用域（del ref），
      Ray 的分布式引用计数会自动回收不再被引用的对象
   2. 增加 object_store_memory 配额
   3. 用 ray.wait() 流式消费结果，而非一次性 ray.get() 全部
   4. 使用 Actor 代替 Object Store 做状态存储（Actor 状态不占 Object Store）
   这类似于 Flink 中 RocksDB 的磁盘溢写机制：内存不够时用磁盘换容量，
   但代价是性能下降。
"""

print("\n" + "=" * 70)
print("  🎉 全部课程完成！你现在已经具备 Ray 基础到进阶的知识体系。")
print("     祝你面试顺利！")
print("=" * 70)
