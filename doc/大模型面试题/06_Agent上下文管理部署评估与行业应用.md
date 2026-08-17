# Agent 上下文管理、部署、评估与行业应用

**角色定位**

你是 Agent 上下文管理、工程部署、质量评估和行业落地方向的资深专家，熟悉上下文裁剪、压缩、拼接、生产部署、多 Agent 协作、Agent 评估、多轮一致性和行业应用。

**使用场景**

我正在准备复杂 Agent 工程化落地相关的技术面试。本文件聚焦 Agent 如何管理上下文、如何部署上线、如何评估质量，以及如何应用到真实行业场景。

**回答目标**

请帮助我从生产系统视角回答 Agent 问题，既能解释上下文和记忆的底层机制，也能说明部署、监控、评估和行业落地的完整方案。

**回答要求**

1. 先明确问题所在的工程层次，例如上下文管理、部署架构、协作机制、评估体系或行业应用。
2. 对上下文裁剪和压缩问题，要说明预算管理、信息分层、检索补偿、摘要更新和退化策略。
3. 对部署和评估问题，要说明基础设施、可靠性、性能、安全、监控指标和质量评估方法。
4. 对行业应用问题，要结合业务流程、数据源、合规约束、风险控制和落地路径。
5. 回答要体现工程权衡，不要只给理想架构。
6. 最后补充知识扩展，并给出一段面试中可以直接复述的总结。

**输出格式**

建议使用“背景问题 → 架构方案 → 关键机制 → 风险与治理 → 评估指标 → 知识扩展 → 面试回答”的结构。

**风格约束**

- 使用中文和 Markdown。
- 明确区分 Context 和 Memory。
- 如果出现括号，请使用英文括号 ()，不要使用中文括号。

---

## 2.35 OpenClaw 和 Hermes Agent 的上下文管理机制是怎样的？它们在设计哲学和实现上有哪些核心差异？

OpenClaw 和 Hermes Agent 是两种具有代表性的 AI Agent 框架，它们在上下文 (Context) 管理上采用了截然不同的设计哲学。理解这两者的差异，有助于深入掌握 Agent 记忆系统的设计权衡。

在进入具体机制之前，需要先区分两个概念：**Context (上下文)** 是当前这一轮实际送进模型窗口的全部材料——system prompt、对话历史、工具调用与返回结果、注入文件、压缩后的摘要等；**Memory (记忆)** 是被保存下来、可跨轮复用、跨会话恢复的持久化数据。信息在磁盘上不等于在这一轮 prompt 里，这是理解两种框架差异的基础。

### 一、OpenClaw 的上下文管理机制

**核心设计哲学**：**"没有写进文件的，不存在"**。所有长期状态必须持久化到磁盘上的 Markdown 文件，优化目标是记忆的**及时性**——让相关记忆在主回复前浮现。

#### 1.1 三层记忆结构

| 层级         | 存储位置               | 内容                      | 加载策略                    |
| ------------ | ---------------------- | ------------------------- | --------------------------- |
| **短期记忆** | `memory/YYYY-MM-DD.md` | 当天活动 append-only 日志 | 当日 + 昨日自动注入 context |
| **近端记忆** | `sessions/` 目录       | 完整会话存档              | 对话过长时冲刷到此          |
| **长期记忆** | `MEMORY.md`            | 偏好、决策、持久事实      | 每次会话自动加载到 context  |

#### 1.2 多级 Compaction 压缩管线

OpenClaw 内置了可插拔的上下文引擎，通过多级压缩应对上下文窗口限制：

```text
┌─────────────────────────────────────────────────────┐
│  Snip: 裁剪中间轮次的冗余内容                        │
│    ↓                                                │
│  Microcompact: 删除无用的工具输出                    │
│    ↓                                                │
│  Context Collapse: 可逆折叠，保留侧链细节            │
│    ↓                                                │
│  Autocompact: 最后手段，生成不可逆摘要               │
│    触发条件：上下文溢出错误 或 API 超时且            │
│             token 使用率 > 65%                       │
└─────────────────────────────────────────────────────┘
```

#### 1.3 Active Recall——核心差异化机制

这是 OpenClaw 最关键的上下文机制：

```text
用户消息到达
    ↓
[Blocker: Active Memory Sub-Agent]   ← 在主回复生成前先跑
    ↓ 调用 memory recall 工具，检索相关历史
    ↓ 生成精简召回结果
    ↓
[注入主回复的隐藏上下文]             ← 作为 untrusted context
    ↓
主模型生成回复
```

- **时机前置**：在主 Agent 开始回答之前，先做一次受限回忆
- **独立模型**：可配置独立的低延迟模型来执行召回
- **按需开启**：默认只对 direct session 启用
- **临时 transcript**：召回过程本身不污染主上下文

#### 1.4 Dreaming 后台巩固系统

通过 Cron 定时任务自动执行三个阶段，将短期信号逐步转化为长期记忆：

```text
原始日志 (Daily Log)
    ↓ Light: 提取当日实体、决策、关键事件
    ↓ REM: 跨日志关联，识别模式趋势
    ↓ Deep: 高置信度模式蒸馏为持久规则，写入 MEMORY.md
```

#### 1.5 Compaction 前的 Memory Flush

压缩发生前，OpenClaw 会先触发 memory flush——让 Agent 先把重要上下文写入 memory 文件，再让摘要压缩旧对话。这是一次**压缩前的抢救**，防止关键信息在压缩中丢失。

### 二、Hermes Agent 的上下文管理机制

**核心设计哲学**：**"把常驻记忆做小，把历史召回放到旁路，强调稳定前缀和 prompt caching 的收益"**。优化目标是上下文的**稳定性**。

#### 2.1 四层记忆架构

| 层级                | 存储方式                                                      | 特点                            |
| ------------------- | ------------------------------------------------------------- | ------------------------------- |
| **瞬时记忆层**      | Redis 缓存                                                    | 毫秒级响应，最大 100 MB/Session |
| **工作记忆层**      | SQLite + FTS5 全文搜索 + 向量索引                             | 跨会话语义检索                  |
| **长期记忆层**      | `MEMORY.md` (2,200 字符硬上限) + `USER.md` (1,375 字符硬上限) | 常驻上下文的高密度事实          |
| **技能层 (Skills)** | Skill Markdown 文件                                           | 可复用的过程性记忆              |

#### 2.2 硬约束驱动的上下文管理

这是 Hermes 最独特的设计：

- **MEMORY.md**：限 **2,200 字符**
- **USER.md**：限 **1,375 字符**
- 写入超限时，add 操作直接失败，把当前所有条目返回给 LLM，让模型自己决策保留什么、删除什么

> 容量有限迫使 Agent 只记重要的事，不重要的自然被挤掉。这与 OpenClaw 的"只进不出"形成鲜明对比。

#### 2.3 Frozen Snapshot 策略

```text
Session 开始时：
  磁盘 MEMORY.md/USER.md → 渲染进 system prompt → 冻结快照

Session 中途：
  新记忆写入 → 只落盘，不改当前 system prompt

下次 Session：
  新 system prompt = 最新磁盘状态
```

**收益**：
- System prompt 不在会话中途抖动
- Anthropic prompt caching 的前缀命中稳定
- KV cache 效率最大化

#### 2.4 双层上下文压缩架构

```text
┌──────────────────────────────────────────────────┐
│  Layer 1: Gateway 预检 (85% 阈值)                 │
│    └─ 消息到达前检查 token 用量，防止炸 API       │
│                                                   │
│  Layer 2: Agent 循环内压缩 (50% 阈值)             │
│    └─ 对话中自动触发，用辅助 LLM 压缩中间轮次     │
└──────────────────────────────────────────────────┘
```

压缩采用 **4 Phase 算法**：
1. **Phase 1**：删除旧工具输出（>200 字符的直接丢弃）
2. **Phase 2**：计算边界，保护头部和尾部最近的消息
3. **Phase 3**：用辅助 LLM 生成结构化摘要
4. **Phase 4**：组装压缩后的消息列表

**结构化摘要格式**：

```text
## Goal — 用户目标
## Constraints & Preferences
## Progress — Done / In Progress / Blocked
## Key Decisions
## Relevant Files
## Next Steps
## Critical Context
```

迭代重压缩时，上次摘要会被**更新而非从头生成**，保持跨轮次的连续性。

#### 2.5 Session Search——旁路历史召回

Hermes 把常驻记忆和 session search 彻底分开：
- **常驻层**：MEMORY.md + USER.md → 每轮都在 context 里
- **历史层**：完整会话存在 SQLite → FTS5 全文搜索 → LLM 摘要 → 临时注入 context

#### 2.6 Nudge Engine——主动记忆触发

Hermes 有可配置的 `nudge_interval`——定时提醒 Agent 回顾历史，检查是否有值得提炼的经验。在 gateway 模式空闲超时前也会主动 flush。

### 三、核心差异对比

| 维度               | OpenClaw                              | Hermes Agent                                  |
| ------------------ | ------------------------------------- | --------------------------------------------- |
| **设计哲学**       | 记忆编排器——让相关记忆在主回复前浮现  | 受控常驻层 + 按需检索层                       |
| **优化目标**       | 记忆的**及时性**                      | 上下文的**稳定性**                            |
| **长期记忆上限**   | 无硬约束（纯追加，易"数字囤积症"）    | 硬约束（2,200 + 1,375 字符）                  |
| **压缩触发**       | 后台 Cron + 故障恢复被动触发          | 写入超限时实时同步触发                        |
| **压缩方法**       | 三阶段提取式巩固，原始数据永存        | 模型自主裁剪 + 淘汰式浓缩，旧条目不可恢复     |
| **召回策略**       | **Active Recall**——回复前主动检索注入 | Session Search——agent 主动调用工具时按需检索  |
| **Prompt Caching** | 不特别优化                            | **Frozen Snapshot** 专门优化前缀缓存命中      |
| **遗忘哲学**       | 不遗忘，只提炼（信息保真度最高）      | 主动选择性遗忘，模仿人类记忆                  |
| **自动化程度**     | 较低（人工提炼为主，Dreaming 默认关） | 较高（Skill 自动蒸馏 + Nudge + 自动记忆写入） |
| **多用户隔离**     | 多 Agent 路由物理隔离                 | 同 Profile 内 USER.md 共享                    |

### 四、上下文窗口即将耗尽时的应对策略

#### 4.1 OpenClaw 的策略

```text
┌──────────────────────────────────────────────────┐
│ 1. Memory Flush                                  │
│    将重要信息紧急写入 memory 文件，防止丢失      │
│    ↓                                             │
│ 2. 多级压缩 (Snip → Microcompact → Collapse)      │
│    逐步释放空间                                  │
│    ↓                                             │
│ 3. Autocompact                                   │
│    最后手段：不可逆摘要，将整个历史压缩为摘要    │
│    ↓                                             │
│ 4. 会话切换                                      │
│    将当前会话存档到 sessions/，开启新会话        │
└──────────────────────────────────────────────────┘
```

#### 4.2 Hermes Agent 的策略

```text
┌──────────────────────────────────────────────────┐
│ 1. 4 Phase 压缩 (50% 阈值触发)                   │
│    生成结构化摘要，保留关键信息                  │
│    ↓                                             │
│ 2. 工具输出裁剪                                  │
│    删除 >200 字符的旧工具输出                    │
│    ↓                                             │
│ 3. 摘要更新（非重建）                            │
│    在已有摘要基础上增量更新，维持连续性           │
│    ↓                                             │
│ 4. 硬约束保护                                    │
│    MEMORY.md 超限 → 强制 LLM 决策保留什么        │
└──────────────────────────────────────────────────┘
```

### 五、代码示例

```python
"""
OpenClaw 与 Hermes Agent 上下文管理机制的简化实现

以下代码展示了两种框架核心机制的概念性实现
"""

import hashlib
import json
import os
import sqlite3
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


# ==========================================
# 共享数据结构
# ==========================================

@dataclass
class Message:
    """消息数据结构"""
    role: str           # user / assistant / system / tool
    content: str
    token_count: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class ContextState:
    """上下文状态"""
    messages: list[Message] = field(default_factory=list)
    total_tokens: int = 0
    system_prompt: str = ""


# ==========================================
# OpenClaw 风格：文件系统即记忆 + Active Recall
# ==========================================

class OpenClawStyleContext:
    """OpenClaw 风格的上下文管理器

    核心特征：
    - 文件系统即记忆（所有状态持久化到 Markdown）
    - 多级压缩管线（Snip → Microcompact → Collapse → Autocompact）
    - Active Recall（回复前主动检索注入）
    - Memory Flush（压缩前紧急抢救）
    """

    def __init__(
        self,
        memory_dir: str = "./memory",
        max_context_tokens: int = 200_000,
        compaction_threshold: float = 0.65,
    ):
        self.memory_dir = memory_dir
        self.max_context_tokens = max_context_tokens
        self.compaction_threshold = compaction_threshold

        os.makedirs(memory_dir, exist_ok=True)

        # 初始化状态
        self.context = ContextState()
        self.memory_file = os.path.join(
            memory_dir, f"{time.strftime('%Y-%m-%d')}.md"
        )
        self.memories_md = os.path.join(memory_dir, "MEMORY.md")

    def _load_long_term_memories(self) -> str:
        """加载长期记忆到上下文"""
        if os.path.exists(self.memories_md):
            with open(self.memories_md, "r") as f:
                content = f.read()
            return f"## 长期记忆\n{content}"
        return ""

    def _write_to_memory(self, content: str):
        """追加写入当天记忆文件"""
        timestamp = time.strftime("%H:%M:%S")
        with open(self.memory_file, "a") as f:
            f.write(f"\n[{timestamp}] {content}\n")

    def active_recall(self, query: str) -> str:
        """Active Recall：在主回复生成前主动检索相关历史

        这是 OpenClaw 最核心的差异化机制——用一个独立的
        子 Agent 在生成回复前检索相关记忆。
        """
        recall_results = []

        # 搜索今天的日志
        if os.path.exists(self.memory_file):
            with open(self.memory_file, "r") as f:
                content = f.read()
            # 简化实现：按关键词匹配
            keywords = set(query.lower().split())
            for line in content.split("\n"):
                if any(kw in line.lower() for kw in keywords):
                    recall_results.append(line)

        # 搜索 MEMORY.md 中的长期记忆
        if os.path.exists(self.memories_md):
            with open(self.memories_md, "r") as f:
                content = f.read()
            for line in content.split("\n"):
                if any(kw in line.lower() for kw in keywords):
                    recall_results.append(line)

        if recall_results:
            return "## 相关记忆\n" + "\n".join(recall_results[-10:])
        return ""

    def memory_flush(self):
        """Memory Flush：压缩前的紧急抢救

        在压缩发生前，先把重要上下文写入 memory 文件，
        防止关键信息在压缩中永久丢失。
        """
        # 从当前上下文中提取关键信息
        key_info = []
        for msg in self.context.messages[-10:]:  # 只看最近10条
            if msg.role == "assistant" and len(msg.content) > 100:
                key_info.append(f"决策: {msg.content[:200]}...")

        if key_info:
            self._write_to_memory("## Memory Flush\n" + "\n".join(key_info))

    def snip(self) -> bool:
        """一级压缩：裁剪中间轮次的冗余内容"""
        if self.context.total_tokens <= self.max_context_tokens:
            return False

        # 保留开头 (system prompt + 前2轮) 和结尾 (后5轮)
        keep_head = min(4, len(self.context.messages))
        keep_tail = min(10, len(self.context.messages))

        kept = (
            self.context.messages[:keep_head]
            + self.context.messages[-keep_tail:]
        )
        self.context.messages = kept
        self._recount_tokens()
        return True

    def microcompact(self) -> bool:
        """二级压缩：删除无用的工具输出"""
        if self.context.total_tokens <= self.max_context_tokens:
            return False

        self.context.messages = [
            msg for msg in self.context.messages
            if not (
                msg.role == "tool"
                and len(msg.content) > 500  # 删除大工具输出
            )
        ]
        self._recount_tokens()
        return True

    def autocompact(self) -> str:
        """三级压缩：生成不可逆摘要（最后手段）"""
        # 触发 memory flush 先抢救
        self.memory_flush()

        # 生成摘要
        summary_parts = []
        for msg in self.context.messages:
            if msg.role in ("user", "assistant"):
                summary_parts.append(
                    f"[{msg.role}@{msg.timestamp:.0f}]: {msg.content[:100]}"
                )

        summary = (
            "## 上下文摘要\n"
            + "\n".join(summary_parts[-20:])  # 最多保留20条摘要
        )

        # 重置上下文，注入摘要
        self.context.messages = [
            Message(
                role="system",
                content=summary,
                token_count=len(summary) // 4,
            )
        ]
        self._recount_tokens()
        return summary

    def _recount_tokens(self):
        """重新计算总 token 数"""
        self.context.total_tokens = sum(
            msg.token_count for msg in self.context.messages
        )

    def prepare_context(self, query: str) -> ContextState:
        """准备上下文——展示 OpenClaw 的完整流程"""
        # Step 1: 加载长期记忆
        ltm = self._load_long_term_memories()
        if ltm:
            self.context.messages.insert(
                0, Message(role="system", content=ltm, token_count=len(ltm) // 4)
            )

        # Step 2: Active Recall
        recalled = self.active_recall(query)
        if recalled:
            self.context.messages.append(
                Message(
                    role="system",
                    content=recalled,
                    token_count=len(recalled) // 4,
                )
            )

        # Step 3: 检查 token 使用率，触发压缩
        usage_ratio = self.context.total_tokens / self.max_context_tokens
        if usage_ratio > self.compaction_threshold:
            if not self.snip():
                if not self.microcompact():
                    self.autocompact()

        return self.context


# ==========================================
# Hermes Agent 风格：硬约束 + Frozen Snapshot
# ==========================================

class HermesStyleContext:
    """Hermes Agent 风格的上下文管理器

    核心特征：
    - 硬约束记忆上限（MEMORY.md 2,200 字符, USER.md 1,375 字符）
    - Frozen Snapshot（Session 开始冻结快照，中途不修改 system prompt）
    - 4 Phase 结构化压缩
    - Session Search（FTS5 旁路召回）
    - Nudge Engine（定时提醒提炼）
    """

    MAX_MEMORY_CHARS = 2_200
    MAX_USER_CHARS = 1_375
    COMPRESS_THRESHOLD = 0.50  # 50% 阈值触发压缩

    def __init__(
        self,
        db_path: str = "./memory.db",
        max_context_tokens: int = 200_000,
    ):
        self.db_path = db_path
        self.max_context_tokens = max_context_tokens

        # 初始化数据库
        self._init_db()

        # Frozen Snapshot
        self._frozen_snapshot: Optional[str] = None
        self._memory_md_content: str = ""
        self._user_md_content: str = ""
        self.context = ContextState()

        # Nudge 计数器
        self._nudge_counter = 0
        self._nudge_interval = 20  # 每 20 轮提醒一次

    def _init_db(self):
        """初始化 SQLite + FTS5 全文搜索"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                messages TEXT,
                summary TEXT,
                created_at REAL
            )
        """)
        # FTS5 全文搜索索引
        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS sessions_fts
            USING fts5(id, messages, summary, content='sessions')
        """)
        self.conn.commit()

    def load_memory_files(self):
        """加载 MEMORY.md 和 USER.md"""
        if os.path.exists("MEMORY.md"):
            with open("MEMORY.md", "r") as f:
                self._memory_md_content = f.read()

        if os.path.exists("USER.md"):
            with open("USER.md", "r") as f:
                self._user_md_content = f.read()

    def create_frozen_snapshot(self):
        """Frozen Snapshot：Session 开始时冻结 system prompt 快照

        关键设计：Session 中途新写入的记忆只落盘，
        不修改当前 system prompt，保证前缀稳定。
        """
        self.load_memory_files()

        snapshot_parts = [
            "You are a helpful AI assistant.",
            "",
        ]

        if self._user_md_content:
            snapshot_parts.append(
                f"## 用户信息\n{self._user_md_content[:self.MAX_USER_CHARS]}"
            )

        if self._memory_md_content:
            snapshot_parts.append(
                f"## 记忆\n{self._memory_md_content[:self.MAX_MEMORY_CHARS]}"
            )

        self._frozen_snapshot = "\n\n".join(snapshot_parts)
        self.context.system_prompt = self._frozen_snapshot

    def write_memory(self, entry: str) -> bool:
        """写入 MEMORY.md——硬约束检查

        Returns:
            True 如果写入成功，False 如果超限需要 LLM 裁剪
        """
        new_entry = f"- {entry}\n"
        new_total = len(self._memory_md_content) + len(new_entry)

        if new_total > self.MAX_MEMORY_CHARS:
            # 超限——返回 false，让 LLM 决策保留什么
            return False

        self._memory_md_content += new_entry
        with open("MEMORY.md", "w") as f:
            f.write(self._memory_md_content)

        # 写入落盘，但不修改当前 frozen snapshot
        return True

    def compress_4phase(self) -> str:
        """4 Phase 结构化压缩"""

        # Phase 1: 删除旧工具输出
        self.context.messages = [
            msg for msg in self.context.messages
            if not (
                msg.role == "tool" and len(msg.content) > 200
            )
        ]

        # Phase 2: 计算边界，保护头部和尾部
        keep_head = min(2, len(self.context.messages))
        keep_tail = min(8, len(self.context.messages))
        middle = self.context.messages[keep_head:-keep_tail]

        # Phase 3: 生成结构化摘要
        summary = self._generate_structured_summary(middle)

        # Phase 4: 组装压缩后的消息列表
        compressed = (
            self.context.messages[:keep_head]
            + [
                Message(
                    role="system",
                    content=summary,
                    token_count=len(summary) // 4,
                )
            ]
            + self.context.messages[-keep_tail:]
        )

        self.context.messages = compressed
        return summary

    def _generate_structured_summary(self, messages: list[Message]) -> str:
        """生成结构化摘要"""
        user_goals = []
        decisions = []
        files = []
        progress = []

        for msg in messages:
            if msg.role == "user":
                user_goals.append(msg.content[:100])
            elif msg.role == "assistant":
                if "决定" in msg.content or "修改" in msg.content:
                    decisions.append(msg.content[:100])
                if "/" in msg.content:
                    # 简化：提取文件路径
                    for word in msg.content.split():
                        if word.startswith("/") or (
                            "." in word and "/" in word
                        ):
                            files.append(word)

        return f"""## Goal
{chr(10).join(user_goals[-3:]) or '继续之前的对话'}

## Key Decisions
{chr(10).join(decisions[-3:]) or '无重大决策'}

## Relevant Files
{chr(10).join(set(files[-5:])) or '无'}

## Progress
{chr(10).join(progress[-5:]) or '进行中'}

## Next Steps
继续当前任务
"""

    def session_search(self, query: str, limit: int = 5) -> list[str]:
        """Session Search：FTS5 全文搜索历史会话

        关键设计：历史召回放在旁路，不污染常驻上下文。
        """
        cursor = self.conn.execute(
            """
            SELECT summary FROM sessions_fts
            WHERE sessions_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, limit),
        )
        return [row[0] for row in cursor.fetchall()]

    def nudge_check(self) -> Optional[str]:
        """Nudge Engine：定时提醒 Agent 提炼记忆"""
        self._nudge_counter += 1

        if self._nudge_counter >= self._nudge_interval:
            self._nudge_counter = 0
            return (
                "[Nudge] 已对话多轮，回顾一下有没有 "
                "值得提炼的经验、偏好或决策？"
            )
        return None

    def prepare_context(self, query: str) -> ContextState:
        """准备上下文——展示 Hermes 的完整流程"""

        # Step 1: 创建 frozen snapshot（session 开始时）
        if not self._frozen_snapshot:
            self.create_frozen_snapshot()

        # Step 2: 检查 token 使用率
        usage_ratio = self.context.total_tokens / self.max_context_tokens
        if usage_ratio > self.COMPRESS_THRESHOLD:
            self.compress_4phase()

        # Step 3: Session Search 旁路召回
        recalled = self.session_search(query)
        if recalled:
            recalled_text = "## 历史相关会话\n" + "\n".join(recalled)
            self.context.messages.append(
                Message(
                    role="system",
                    content=recalled_text,
                    token_count=len(recalled_text) // 4,
                )
            )

        # Step 4: Nudge 提醒
        nudge = self.nudge_check()
        if nudge:
            self.context.messages.append(
                Message(
                    role="system",
                    content=nudge,
                    token_count=len(nudge) // 4,
                )
            )

        return self.context


# ==========================================
# 对比演示
# ==========================================

def demonstrate_openclaw_flow():
    """演示 OpenClaw 的上下文准备流程"""
    print("=" * 60)
    print("OpenClaw 上下文准备流程")
    print("=" * 60)

    ctx = OpenClawStyleContext(memory_dir="./demo_memory_openclaw")

    # 模拟一些已有记忆
    ctx._write_to_memory("用户偏好：使用 Python")
    ctx._write_to_memory("决策：使用 FastAPI 框架")

    # 模拟当前上下文
    ctx.context.messages = [
        Message(role="user", content="帮我写一个 API 服务",
                token_count=5),
    ]
    ctx.context.total_tokens = 5

    # 准备上下文
    result = ctx.prepare_context("API 服务 Python 框架")
    print(f"上下文消息数: {len(result.messages)}")
    print(f"总 Token: {result.total_tokens}")
    print()
    for msg in result.messages:
        print(f"  [{msg.role}]: {msg.content[:80]}...")


def demonstrate_hermes_flow():
    """演示 Hermes 的上下文准备流程"""
    print("=" * 60)
    print("Hermes Agent 上下文准备流程")
    print("=" * 60)

    ctx = HermesStyleContext(db_path="./demo_memory_hermes.db")

    # 创建初始记忆文件
    with open("MEMORY.md", "w") as f:
        f.write("- 用户是 Python 开发者\n- 偏好 FastAPI\n")
    with open("USER.md", "w") as f:
        f.write("技术栈: Python, FastAPI, PostgreSQL\n")

    # Session 开始——创建 frozen snapshot
    ctx.create_frozen_snapshot()
    print(f"Frozen Snapshot 长度: {len(ctx._frozen_snapshot or '')} 字符")

    # 模拟写入记忆
    success = ctx.write_memory("新学到：用户喜欢用 Pydantic v2")
    print(f"写入记忆: {'成功' if success else '失败（超限）'}")

    # 验证 snapshot 不变
    print(f"Snapshot 变化: {'是' if ctx._frozen_snapshot != ctx.context.system_prompt else '否'}")

    # 清理
    if os.path.exists("MEMORY.md"):
        os.remove("MEMORY.md")
    if os.path.exists("USER.md"):
        os.remove("USER.md")


# 运行演示
if __name__ == "__main__":
    demonstrate_openclaw_flow()
    print()
    demonstrate_hermes_flow()
    print()

    print("=" * 60)
    print("核心差异总结")
    print("=" * 60)
    print("""
    OpenClaw:
      → 文件系统即记忆，什么都记，不遗忘
      → Active Recall 在回复前主动检索
      → 多级压缩 + Memory Flush 抢救
      → 优化：记忆的及时性

    Hermes Agent:
      → 硬约束上限，强制选择性遗忘
      → Frozen Snapshot 保证前缀稳定
      → 4 Phase 结构化压缩 + Session Search 旁路召回
      → 优化：上下文的稳定性
    """)
```

### 六、知识扩展

- **Token 计数与上下文窗口监控**：理解 OpenClaw 和 Hermes 的上下文管理机制，需要先理解 Token 计数的底层原理和上下文窗口的使用量监控，这是压缩策略触发的判断依据。
- **Prompt Caching 原理**：Hermes 的 Frozen Snapshot 策略专门优化了 prompt caching 的前缀命中率，理解 Anthropic/OpenAI 的 prompt caching 机制有助于理解为什么要设计"冻结快照"。
- **记忆机制**：上下文管理是记忆系统的一部分，理解长短期记忆的分类框架有助于理解 OpenClaw 和 Hermes 的记忆分层设计。
- **Agent 循环 (Agent Loop)**：上下文管理是 Agent 循环中上下文准备阶段的核心逻辑，理解 Agent 循环有助于理解上下文管理在整体架构中的位置。
- **压缩算法 (Compaction)**：两种框架都涉及上下文的压缩，理解文本摘要、信息提取等压缩技术有助于深入理解其实现。
- **SubAgent 机制**：OpenClaw 的 Active Recall 使用了一个子 Agent 做记忆检索，这与 SubAgent 的上下文传递机制有直接关联。
- **多 Agent 协作**：两种框架的不同设计哲学影响了它们在多 Agent 场景中的表现，理解多 Agent 协作有助于理解不同设计哲学的适用场景。

### 完整口头回答

OpenClaw 和 Hermes Agent 在上下文管理上代表了两种截然不同的设计哲学。

OpenClaw 的核心是"文件系统即记忆"，所有状态持久化到 Markdown 文件。它最关键的机制是 Active Recall——在主回复生成前，用一个独立的子 Agent 检索相关历史记忆并注入上下文，确保模型在回答前"回忆"起相关信息。此外还有多级压缩管线（Snip → Microcompact → Collapse → Autocompact）应对上下文窗口压力，以及 Compression 前的 Memory Flush 机制防止关键信息在压缩中丢失。还有 Dreaming 后台巩固系统，通过 Cron 定时任务逐步将短期日志提炼为长期记忆。它的设计哲学是"不遗忘，只提炼"，优化记忆的及时性。

Hermes Agent 的核心是"把常驻记忆做小，把历史召回放旁路"。它有三个独特设计：第一是硬约束驱动——MEMORY.md 限制 2,200 字符，USER.md 限制 1,375 字符，超限时让 LLM 决策保留什么，强制选择性遗忘；第二是 Frozen Snapshot 策略——Session 开始时将记忆文件冻结为 system prompt 快照，中途新记忆只落盘不修改 prompt，保证前缀稳定以最大化 prompt caching 命中率；第三是 Session Search 旁路召回——完整会话存 SQLite，需要时通过 FTS5 全文搜索按需检索。压缩采用 4 Phase 算法并生成结构化摘要。还有 Nudge Engine 定时提醒 Agent 提炼经验。它的设计哲学是"主动选择性遗忘"，优化上下文的稳定性。

核心差异在于：OpenClaw 像一个无限记事本，什么都记、什么都保留、在回复前主动帮你回忆，但长期运行可能"数字囤积"；Hermes Agent 像一个会打理记忆的智能伙伴，常驻记忆小而精、上下文稳定不抖动、主动遗忘噪音，但硬上限可能挤掉低频但重要的信息。

## 2.36 在大模型应用中，上下文窗口的裁剪和压缩具体该怎么做？裁剪策略有哪些？压缩 Prompt 该如何设计？

当对话长度超过模型上下文窗口限制时（如 200K tokens），必须对上下文进行裁剪 (Trimming) 或压缩 (Compaction) 来腾出空间。裁剪是直接删除部分内容，压缩是生成摘要替代原内容。二者通常配合使用。

### 一、上下文裁剪策略

裁剪的核心是**决定保留什么、丢弃什么**。裁得太多会丢失关键上下文（产生"失忆"问题），裁得太少则无效。

#### 1.1 基于位置的裁剪

**策略描述**：根据消息在对话历史中的位置来决定保留或丢弃。

```text
完整对话历史 [msg_1, msg_2, ..., msg_n]，总 token 数 > 窗口限制

策略 A: 保留头部 + 尾部（最常见）
  保留: [msg_1, msg_2]          ← 头部（初始任务定义）
        [msg_{n-4}, ..., msg_n]  ← 尾部（最近对话）
  丢弃: [msg_3, ..., msg_{n-5}]  ← 中间

策略 B: 仅保留尾部
  保留: [msg_{n-k}, ..., msg_n]  ← 最近 k 轮
  丢弃: [msg_1, ..., msg_{n-k-1}]

策略 C: 滑动窗口
  保留: 最近 N 轮对话
  丢弃: 超出 N 轮的部分
```

**适用场景**：
- 策略 A：任务定义在对话开头时（如 System Prompt 中有详细指令）
- 策略 B：聊天类应用，不依赖早期上下文
- 策略 C：需要对对话深度做硬性限制

#### 1.2 基于优先级的裁剪

**策略描述**：为每条消息分配重要度分数，保留高分消息。

```python
# 优先级评分规则
PRIORITY_RULES = {
    "system_prompt":      10,   # 最高优先级，必保留
    "user_question":      8,    # 用户问题（尤其是当前轮）
    "tool_call":          7,    # 工具调用（含参数信息）
    "tool_result_small":  6,    # 小型工具结果（<500 tokens）
    "assistant_decision": 5,    # 助手的关键决策/修改
    "assistant_reply":    3,    # 普通助手回复
    "tool_result_large":  2,    # 大型工具结果（>2000 tokens）
    "acknowledgment":     1,    # 确认性消息（"好的""收到"）
}
```

**实现要点**：
- System Prompt 和当前用户问题**绝对不可丢弃**
- 工具调用的参数比工具输出更重要（参数承载意图，输出可被摘要替代）
- 纯确认性消息优先丢弃

#### 1.3 基于语义的裁剪

**策略描述**：利用 Embedding 或 LLM 判断每条消息与当前任务的关联度。

```text
1. 将当前用户问题编码为向量 q
2. 将对话历史中每条消息编码为向量 {h_1, h_2, ..., h_n}
3. 计算 cosine_similarity(q, h_i)
4. 保留相似度最高的 top-K 条消息
```

**优缺点**：
- 优点：相关性保留最精准
- 缺点：计算成本高（每条消息都要编码），实时性差

#### 1.4 裁剪的综合策略

实践中通常组合使用：

```text
┌──────────────────────────────────────────────────────┐
│              上下文裁剪决策流程                       │
├──────────────────────────────────────────────────────┤
│                                                      │
│  1. 硬性保留区                                       │
│     - System Prompt（永远保留）                      │
│     - 当前轮用户问题（永远保留）                     │
│     - 最近 N 轮对话（默认保留）                      │
│                                                      │
│  2. 优先级排序区                                     │
│     - 对中间区域的消息按优先级打分                   │
│     - 按分数从高到低填充剩余 Token 预算              │
│                                                      │
│  3. 裁剪执行                                         │
│     - 超出预算的低优先级消息直接丢弃                 │
│     - 重要但过长的消息先压缩再保留                   │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### 二、上下文压缩策略

压缩的核心是**用更少的 Token 保留更多信息**。与裁剪不同，压缩后的内容仍存在于上下文中，只是被浓缩了。

#### 2.1 压缩的本质

```text
压缩前 (5000 tokens):
  用户: 帮我写一个 Python 脚本来处理 CSV 文件
  助手: 好的，我来写一个脚本。[长代码]
  用户: 这个脚本有个 bug，读取大文件时会内存溢出
  助手: 这是因为用了 read() 一次性加载整个文件...[长解释 + 修改后代码]
  用户: 还是有问题，能否用 pandas 分块读取？
  助手: 可以，pandas 的 read_csv 支持 chunksize 参数...[长代码]

压缩后 (~200 tokens):
  [压缩摘要]
  ## Goal: 编写处理 CSV 文件的 Python 脚本
  ## Progress:
  - V1: 基础 CSV 读取脚本（已完成，有内存问题）
  - V2: pandas chunksize 分块读取（进行中）
  ## Key Decisions: 使用 pandas read_csv + chunksize 参数
  ## Relevant Files: process_csv.py
  ## Critical Context: 需要处理大文件，注意内存管理
```

**Token 节省比**：约 25:1（5000 → 200 tokens）

#### 2.2 渐进式压缩策略

```text
Level 0: 无压缩 — 保留原始消息
    ↓ Token 使用率 > 60%
Level 1: 轻量裁剪 — 删除纯确认消息、去除重复内容
    ↓ Token 使用率 > 75%
Level 2: 工具输出裁剪 — 删除 >500 token 的旧工具结果
    ↓ Token 使用率 > 85%
Level 3: 结构化摘要 — 用压缩 Prompt 生成摘要替代中间轮次
    ↓ Token 使用率 > 95%
Level 4: 激进压缩 — 仅保留 System Prompt + 当前轮 + 最终摘要
```

#### 2.3 压缩内容的选择

**应该压缩的内容**：
- 中间轮次的冗长工具输出（尤其是已经处理完的结果）
- 多轮的错误修复过程（保留最终方案，压缩尝试过程）
- 重复内容（多次出现的相同信息）

**不应该压缩的内容**：
- 用户的核心需求和约束条件
- 关键的决策点（"选择用 Redis 而不是 MySQL"）
- 尚未完成的待办事项
- 当前轮的用户输入
- System Prompt 中的行为约束

### 三、压缩 Prompt 设计

这是整个压缩机制中最关键的一环——Prompt 的质量直接决定了压缩后信息的完整度。

#### 3.1 结构化摘要 Prompt

最常用的方式，将对话历史压缩为固定格式的结构化摘要：

```text
你是一个对话压缩助手。请将以下对话历史压缩为结构化摘要。
压缩规则：
1. 保留所有用户目标和约束条件
2. 保留所有关键决策及其理由
3. 保留未完成的任务和待办事项
4. 保留被修改/创建的文件路径
5. 压缩代码实现细节，只保留方案思路
6. 丢弃错误尝试过程，保留最终正确方案
7. 丢弃纯确认性对话（如"好的""收到"）

## 输出格式（严格遵循，不要添加额外内容）

### Goal
[用户的核心目标，一句话概括]

### Constraints
- [约束条件 1]
- [约束条件 2]

### Progress
- [已完成的事项]
- [进行中的事项]
- [被阻塞的事项]

### Key Decisions
- [关键决策 1]：理由
- [关键决策 2]：理由

### Relevant Files
- [文件路径 1]：[文件用途]

### Next Steps
1. [下一步 1]
2. [下一步 2]

### Critical Context
[其他必须保留的关键上下文]

---

## 待压缩的对话历史
{dialog_history}

## 结构化摘要
```

#### 3.2 增量更新 Prompt

当已有一次摘要后，后续压缩应该更新摘要而非重建：

```text
你是一个对话压缩助手。以下是一段已有的对话摘要和新的对话内容。
请在已有摘要的基础上进行增量更新，不要完全重建。

## 已有摘要
{existing_summary}

## 新增对话
{new_messages}

## 更新要求
1. Goal 和 Constraints 除非有变化，否则保持不变
2. Progress 部分：将已完成的新事项加入 Done，更新 In Progress
3. Key Decisions：仅追加新的决策，保留旧决策
4. Relevant Files：追加新涉及的文件
5. Next Steps：用最新的待办事项替换
6. Critical Context：合并新旧关键上下文

## 更新后的摘要
```

#### 3.3 分层摘要 Prompt

对于非常长的对话，可以先生成每段的摘要，再对摘要做摘要：

```text
# 第一层：分段摘要
[对话片段 1 ~ 100 轮] → 摘要 1
[对话片段 101 ~ 200 轮] → 摘要 2
[对话片段 201 ~ 300 轮] → 摘要 3

# 第二层：摘要的摘要
[摘要 1, 摘要 2, 摘要 3] + 当前对话 → 最终摘要
```

对应的 Prompt：

```text
你是一个对话压缩助手。以下是多段对话摘要，请合并为一个最终摘要。

## 要求
1. 合并相同的 Goal（如果有多个，取最新的）
2. 去重重复的关键决策
3. 按时间顺序排列 Progress
4. 合并 Relevant Files 列表（去重）
5. 提取最新的 Next Steps

## 摘要 1
{summary_1}

## 摘要 2
{summary_2}

## 摘要 3
{summary_3}

## 当前对话
{current_messages}

## 最终摘要（严格遵循之前的输出格式）
```

#### 3.4 压缩 Prompt 设计原则

| 原则               | 说明                                   | 示例                     |
| ------------------ | -------------------------------------- | ------------------------ |
| **明确输出格式**   | 指定结构化字段，避免摘要散乱           | JSON / Markdown 固定模板 |
| **区分保留与丢弃** | 明确告诉模型什么必须保留、什么可以丢弃 | "保留决策，丢弃尝试过程" |
| **限制输出长度**   | 控制摘要本身的大小                     | "摘要不超过 300 字"      |
| **增量优于重建**   | 更新已有摘要比每次重建更稳定           | 传入 existing_summary    |
| **验证关键信息**   | 压缩后检查关键信息是否丢失             | 对比前后 Goals/Decisions |
| **保留可恢复路径** | 文件路径、行号等让信息可追溯           | "在 xxx.py:42 修改了..." |

### 四、代码示例

```python
"""
上下文裁剪与压缩的完整实现示例

包含：基于优先级的裁剪、结构化摘要压缩、增量更新
"""

import json
import re
import tiktoken
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ==========================================
# 基础数据结构
# ==========================================

class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    role: MessageRole
    content: str
    token_count: int = 0

    def __post_init__(self):
        if self.token_count == 0:
            # 简化 Token 估算：英文 1 token ≈ 4 字符，中文 1 token ≈ 1.5 字符
            chinese_chars = len(re.findall(r'[一-鿿]', self.content))
            other_chars = len(self.content) - chinese_chars
            self.token_count = int(chinese_chars / 1.5 + other_chars / 4)


@dataclass
class ContextWindow:
    messages: list[Message] = field(default_factory=list)
    max_tokens: int = 200_000

    @property
    def total_tokens(self) -> int:
        return sum(m.token_count for m in self.messages)

    @property
    def usage_ratio(self) -> float:
        return self.total_tokens / self.max_tokens


# ==========================================
# 优先级评分
# ==========================================

class PriorityScorer:
    """为每条消息分配优先级分数"""

    # 优先级规则：分数越高越重要
    RULES = {
        "system_prompt": 10,
        "user_question": 8,
        "tool_call": 7,
        "tool_result_small": 6,
        "assistant_decision": 5,
        "assistant_reply": 3,
        "tool_result_large": 2,
        "acknowledgment": 1,
    }

    # 关键决策关键词
    DECISION_KEYWORDS = [
        "决定", "选择", "修改方案", "改为", "最终采用",
        "结论是", "确定了", "修改了", "创建了", "删除了"
    ]

    # 确认性消息模式
    ACK_PATTERNS = [
        r'^好的[，。]?$', r'^收到[，。]?$', r'^OK[，。]?$',
        r'^明白了[，。]?$', r'^了解[，。]?$', r'^没问题[，。]?$',
    ]

    @classmethod
    def score(cls, msg: Message, is_current_round: bool = False) -> int:
        """计算消息的优先级分数"""

        # 当前轮消息最高优先级
        if is_current_round:
            return 10

        # System Prompt 最高优先级
        if msg.role == MessageRole.SYSTEM:
            return cls.RULES["system_prompt"]

        # 用户问题
        if msg.role == MessageRole.USER:
            return cls.RULES["user_question"]

        # 工具调用
        if msg.role == MessageRole.TOOL:
            # 判断是否包含决策信息
            if any(kw in msg.content for kw in cls.DECISION_KEYWORDS):
                return cls.RULES["assistant_decision"]

            if len(msg.content) < 500:
                return cls.RULES["tool_result_small"]
            return cls.RULES["tool_result_large"]

        # 助手回复
        if msg.role == MessageRole.ASSISTANT:
            # 检查是否为确认性消息
            for pattern in cls.ACK_PATTERNS:
                if re.match(pattern, msg.content.strip()):
                    return cls.RULES["acknowledgment"]

            # 检查是否包含关键决策
            if any(kw in msg.content for kw in cls.DECISION_KEYWORDS):
                return cls.RULES["assistant_decision"]

            return cls.RULES["assistant_reply"]

        return 1  # 默认最低


# ==========================================
# 上下文裁剪器
# ==========================================

class ContextTrimmer:
    """上下文裁剪器：基于优先级 + 位置策略"""

    def __init__(
        self,
        max_tokens: int = 200_000,
        keep_head: int = 3,    # 保留头部 N 条消息
        keep_tail: int = 8,    # 保留尾部 N 条消息
        current_round_size: int = 4,  # 当前轮消息数
    ):
        self.max_tokens = max_tokens
        self.keep_head = keep_head
        self.keep_tail = keep_tail
        self.current_round_size = current_round_size

    def trim(self, messages: list[Message]) -> list[Message]:
        """执行裁剪"""

        if not messages:
            return messages

        total = sum(m.token_count for m in messages)
        if total <= self.max_tokens:
            return messages  # 不需要裁剪

        # Step 1: 标记硬性保留区
        n = len(messages)
        current_round_start = max(0, n - self.current_round_size)

        # 硬性保留的消息索引
        reserved_indices = set()
        reserved_indices.update(range(min(self.keep_head, n)))  # 头部
        reserved_indices.update(range(max(self.keep_head, current_round_start), n))  # 尾部（含当前轮）

        # Step 2: 对中间区域评分
        middle_messages = []
        for i in range(self.keep_head, current_round_start):
            is_current = i >= current_round_start
            score = PriorityScorer.score(messages[i], is_current)
            middle_messages.append((i, score, messages[i]))

        # 按分数降序排列
        middle_messages.sort(key=lambda x: x[1], reverse=True)

        # Step 3: 按预算填充
        kept = []
        used_tokens = 0

        # 先放入硬性保留的头部
        for i in range(self.keep_head):
            if i < n and i in reserved_indices:
                kept.append(messages[i])
                used_tokens += messages[i].token_count

        # 从中间区域按优先级填充
        remaining_budget = int(self.max_tokens * 0.95)  # 留 5% 余量
        for i, score, msg in middle_messages:
            if used_tokens + msg.token_count > remaining_budget:
                break
            kept.append(msg)
            used_tokens += msg.token_count

        # 放入硬性保留的尾部（当前轮必须保留）
        for i in range(current_round_start, n):
            if i in reserved_indices:
                kept.append(messages[i])
                used_tokens += messages[i].token_count

        dropped = n - len(kept)
        if dropped > 0:
            print(f"[Trimmer] 裁剪了 {dropped}/{n} 条消息 "
                  f"(Token: {total} → {used_tokens})")

        return kept


# ==========================================
# 上下文压缩器
# ==========================================

class ContextCompactor:
    """上下文压缩器：结构化摘要 + 增量更新"""

    COMPRESSION_PROMPT = """你是一个对话压缩助手。请将以下对话历史压缩为结构化摘要。
压缩规则：
1. 保留所有用户目标和约束条件
2. 保留所有关键决策及其理由
3. 保留未完成的任务和待办事项
4. 保留被修改/创建的文件路径
5. 压缩代码实现细节，只保留方案思路
6. 丢弃错误尝试过程，保留最终正确方案
7. 丢弃纯确认性对话

## 输出格式（严格 JSON）

{{
  "goal": "用户的核心目标",
  "constraints": ["约束1", "约束2"],
  "progress": {{
    "done": ["已完成事项1"],
    "in_progress": ["进行中事项1"],
    "blocked": []
  }},
  "key_decisions": [
    {{"decision": "决策内容", "reason": "理由"}}
  ],
  "relevant_files": ["文件路径"],
  "next_steps": ["下一步1"],
  "critical_context": "其他必须保留的关键上下文"
}}

---

## 待压缩的对话历史
{dialog_history}

## 结构化摘要（JSON）"""

    INCREMENTAL_PROMPT = """你是一个对话压缩助手。请在已有摘要基础上增量更新。

## 已有摘要
{existing_summary}

## 新增对话
{new_messages}

## 更新要求
1. Goal 和 Constraints 除非有变化，否则保持不变
2. Progress：将已完成的新事项加入 done，更新 in_progress
3. Key Decisions：仅追加新的，保留旧的
4. Relevant Files：追加新文件（去重）
5. Next Steps：用最新的替换
6. Critical Context：合并新旧

## 更新后的摘要（严格 JSON，格式与已有摘要相同）"""

    def __init__(self, llm_call):
        """
        Args:
            llm_call: LLM 调用函数，签名为 (prompt: str) -> str
        """
        self.llm_call = llm_call
        self._last_summary: Optional[dict] = None

    def compress(self, messages: list[Message]) -> dict:
        """初次压缩：将消息列表压缩为结构化摘要"""
        dialog_text = self._messages_to_text(messages)
        prompt = self.COMPRESSION_PROMPT.format(dialog_history=dialog_text)
        response = self.llm_call(prompt)
        summary = self._parse_summary(response)
        self._last_summary = summary
        return summary

    def incremental_compress(
        self, new_messages: list[Message]
    ) -> dict:
        """增量压缩：在已有摘要基础上更新"""
        if not self._last_summary:
            return self.compress(new_messages)

        existing_text = json.dumps(
            self._last_summary, ensure_ascii=False, indent=2
        )
        new_text = self._messages_to_text(new_messages)
        prompt = self.INCREMENTAL_PROMPT.format(
            existing_summary=existing_text,
            new_messages=new_text
        )
        response = self.llm_call(prompt)
        summary = self._parse_summary(response)
        self._last_summary = summary
        return summary

    def get_last_summary(self) -> Optional[dict]:
        return self._last_summary

    @staticmethod
    def _messages_to_text(messages: list[Message]) -> str:
        lines = []
        for msg in messages:
            role_map = {
                MessageRole.SYSTEM: "System",
                MessageRole.USER: "User",
                MessageRole.ASSISTANT: "Assistant",
                MessageRole.TOOL: "Tool",
            }
            role_name = role_map.get(msg.role, str(msg.role))
            # 截断过长的内容
            content = msg.content
            if len(content) > 2000:
                content = content[:2000] + "\n... [已截断]"
            lines.append(f"[{role_name}] {content}")
        return "\n\n".join(lines)

    @staticmethod
    def _parse_summary(response: str) -> dict:
        """从 LLM 响应中提取 JSON"""
        # 尝试提取 JSON 块
        json_match = re.search(
            r'```(?:json)?\s*(\{.*?\})\s*```',
            response, re.DOTALL
        )
        if json_match:
            return json.loads(json_match.group(1))

        # 尝试直接解析整个响应
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))

        raise ValueError(f"无法从响应中提取 JSON: {response[:200]}...")


# ==========================================
# 综合上下文管理器
# ==========================================

class ContextManager:
    """综合上下文管理器：组合裁剪和压缩"""

    def __init__(
        self,
        max_tokens: int = 200_000,
        llm_call=None,
        # 触发阈值
        trim_threshold: float = 0.75,     # 75% 触发裁剪
        compact_threshold: float = 0.85,  # 85% 触发压缩
        aggressive_threshold: float = 0.95,  # 95% 触发激进压缩
    ):
        self.max_tokens = max_tokens
        self.trimmer = ContextTrimmer(max_tokens=max_tokens)
        self.compactor = ContextCompactor(llm_call) if llm_call else None
        self.trim_threshold = trim_threshold
        self.compact_threshold = compact_threshold
        self.aggressive_threshold = aggressive_threshold

    def manage(self, messages: list[Message]) -> list[Message]:
        """管理上下文：根据使用率自动裁剪或压缩"""
        total = sum(m.token_count for m in messages)
        ratio = total / self.max_tokens

        print(f"[ContextManager] Token 使用率: {ratio:.1%} ({total}/{self.max_tokens})")

        # Level 0: 正常，无需处理
        if ratio < self.trim_threshold:
            return messages

        # Level 1: 轻量裁剪
        if ratio < self.compact_threshold:
            print("[ContextManager] → 触发轻量裁剪")
            return self.trimmer.trim(messages)

        # Level 2: 压缩中间轮次
        if ratio < self.aggressive_threshold and self.compactor:
            print("[ContextManager] → 触发结构化压缩")
            return self._compact_middle(messages)

        # Level 3: 激进压缩
        if self.compactor:
            print("[ContextManager] → 触发激进压缩")
            return self._aggressive_compact(messages)

        # 兜底：裁剪
        return self.trimmer.trim(messages)

    def _compact_middle(self, messages: list[Message]) -> list[Message]:
        """压缩中间轮次，保留头部和尾部"""
        n = len(messages)
        head_size = 3
        tail_size = 6

        if n <= head_size + tail_size:
            return self.trimmer.trim(messages)

        # 提取中间部分进行压缩
        middle = messages[head_size:-tail_size]
        head = messages[:head_size]
        tail = messages[-tail_size:]

        # 压缩中间
        summary_dict = self.compactor.compress(middle)
        summary_text = self._summary_to_text(summary_dict)
        summary_msg = Message(
            role=MessageRole.SYSTEM,
            content=summary_text
        )

        # 组装：头部 + 摘要 + 尾部
        return head + [summary_msg] + tail

    def _aggressive_compact(self, messages: list[Message]) -> list[Message]:
        """激进压缩：全部压缩为摘要，仅保留当前轮"""
        n = len(messages)
        tail_size = 4  # 保留最后 4 条（当前轮）

        if n < tail_size:
            return messages

        history = messages[:-tail_size]
        current = messages[-tail_size:]

        # 如果已有增量摘要，使用增量更新
        if self.compactor.get_last_summary():
            summary_dict = self.compactor.incremental_compress(history)
        else:
            summary_dict = self.compactor.compress(history)

        summary_text = self._summary_to_text(summary_dict)
        summary_msg = Message(
            role=MessageRole.SYSTEM,
            content=summary_text
        )

        return [summary_msg] + current

    @staticmethod
    def _summary_to_text(summary: dict) -> str:
        """将结构化摘要转为可注入上下文的文本"""
        parts = ["[上下文摘要]"]

        if summary.get("goal"):
            parts.append(f"目标: {summary['goal']}")

        constraints = summary.get("constraints", [])
        if constraints:
            parts.append(f"约束: {', '.join(constraints)}")

        progress = summary.get("progress", {})
        if progress:
            done = progress.get("done", [])
            in_prog = progress.get("in_progress", [])
            blocked = progress.get("blocked", [])
            if done:
                parts.append(f"已完成: {'; '.join(done)}")
            if in_prog:
                parts.append(f"进行中: {'; '.join(in_prog)}")
            if blocked:
                parts.append(f"阻塞: {'; '.join(blocked)}")

        decisions = summary.get("key_decisions", [])
        if decisions:
            decisions_text = "; ".join(
                f"{d.get('decision', '')}({d.get('reason', '')})"
                for d in decisions
            )
            parts.append(f"关键决策: {decisions_text}")

        files = summary.get("relevant_files", [])
        if files:
            parts.append(f"相关文件: {', '.join(files)}")

        next_steps = summary.get("next_steps", [])
        if next_steps:
            parts.append(f"下一步: {'; '.join(next_steps)}")

        critical = summary.get("critical_context", "")
        if critical:
            parts.append(f"关键上下文: {critical}")

        return "\n".join(parts)


# ==========================================
# 使用示例
# ==========================================

def mock_llm(prompt: str) -> str:
    """模拟 LLM 调用（实际使用时替换为真实 API）"""
    return json.dumps({
        "goal": "处理 CSV 文件并生成报告",
        "constraints": ["需要处理大文件", "注意内存管理"],
        "progress": {
            "done": ["基础 CSV 读取脚本已完成"],
            "in_progress": ["使用 pandas chunksize 分块读取"],
            "blocked": []
        },
        "key_decisions": [
            {"decision": "使用 pandas read_csv + chunksize", "reason": "内存有限"}
        ],
        "relevant_files": ["process_csv.py", "data/sample.csv"],
        "next_steps": ["完成分块读取逻辑", "添加进度条"],
        "critical_context": "用户需要处理 10GB+ 的 CSV 文件"
    }, ensure_ascii=False)


if __name__ == "__main__":
    # 模拟长对话
    messages = [
        Message(MessageRole.SYSTEM, "你是一个 Python 编程助手"),
        Message(MessageRole.USER, "帮我写一个处理 CSV 的脚本"),
        Message(MessageRole.ASSISTANT, "好的，这是基础脚本",
                token_count=5000),
        Message(MessageRole.TOOL, "文件内容: ... [5000 字符]",
                token_count=5000),
        Message(MessageRole.USER, "有 bug，内存溢出"),
        Message(MessageRole.ASSISTANT, "好的"),  # 确认性消息，低优先级
        Message(MessageRole.ASSISTANT, "改用 pandas chunksize，关键决策: 使用分块读取",
                token_count=3000),
        Message(MessageRole.USER, "加上进度条"),
    ]

    # 初始化管理器
    manager = ContextManager(
        max_tokens=20000,  # 故意设小以触发压缩
        llm_call=mock_llm,
    )

    # 模拟超过限制
    for msg in messages:
        msg.token_count = max(msg.token_count, 1000)

    result = manager.manage(messages)
    print(f"\n处理后消息数: {len(result)}")
    for i, msg in enumerate(result):
        print(f"  [{i}] {msg.role.value}: {msg.content[:80]}...")
```

### 五、知识扩展

- **向量检索增强 (RAG)**：裁剪和压缩是"减法"，RAG 是"加法"——通过检索将外部知识注入上下文。二者互补，共同管理上下文窗口。
- **Prompt Caching**：压缩导致的 System Prompt 变化会破坏前缀缓存命中率。这就是 Hermes Agent 采用 Frozen Snapshot 策略的原因——宁愿不更新 System Prompt，也要保持缓存命中。
- **自动上下文窗口检测**：在实际系统中，需要实时监控 Token 使用量，在接近上限前提前触发压缩。理解 Token 计数的底层实现有助于正确设置触发阈值。
- **压缩质量评估**：如何验证压缩没有丢失关键信息？可以通过对比压缩前后的任务完成率、关键决策保留率等指标来评估压缩质量。
- **Human-in-the-loop 压缩**：对于高风险场景（如医疗、金融），可以在压缩后让用户确认摘要是否准确，确保关键信息不丢失。
- **模型差异**：不同模型的压缩效果不同。Some 模型擅长摘要（如 Claude），有些则可能丢失细节。压缩 Prompt 需要根据目标模型的特点进行调整。
- **多模态上下文压缩**：如果上下文中包含图片、音频等多模态内容，裁剪和压缩策略需要额外考虑多模态数据的特殊性。
- **上下文隔离**：在多 Agent 系统中，子 Agent 的上下文裁剪是一种"隔离"手段——通过限制传入的上下文范围来控制子 Agent 的视野和权限。

### 完整口头回答

上下文裁剪和压缩是管理上下文窗口的两种核心手段。裁剪是直接删除部分内容，压缩是生成摘要替代原内容，二者通常配合使用。

裁剪有三种主要策略。第一种是基于位置的裁剪：保留头部（初始任务定义）和尾部（最近对话），丢弃中间部分，这是最简单实用的方式。第二种是基于优先级的裁剪：为每条消息打分（System Prompt 10 分、用户问题 8 分、工具调用 7 分、确认性消息 1 分），按分数从高到低填充 Token 预算，低分消息丢弃。第三种是基于语义的裁剪：用 Embedding 计算每条消息与当前任务的关联度，保留相关度最高的。实践中通常组合使用：硬性保留区（System Prompt + 当前轮 + 最近 N 轮）+ 优先级排序区（中间消息按分数填充预算）。

压缩的策略是生成结构化摘要替代原始对话。压缩采取渐进式：Token 使用率超过 60% 时轻量裁剪确认消息，超过 75% 时裁剪大型工具输出，超过 85% 时生成结构化摘要，超过 95% 时激进压缩到仅保留 System Prompt + 摘要 + 当前轮。压缩摘要应采用增量更新而非每次重建，这样既能保持跨轮次的连续性，又能节省计算成本。

压缩 Prompt 的设计是最关键的一环。结构化摘要 Prompt 需要明确：保留什么（目标、约束、决策、待办、文件路径）、丢弃什么（错误尝试、确认性对话、冗余工具输出）、输出什么格式（固定 JSON/Markdown 模板）。增量更新时传入已有摘要，让模型在此基础上更新而非重建。分层压缩时先对片段生成摘要，再对摘要做摘要。核心原则是：明确输出格式、区分保留与丢弃、限制输出长度、增量优于重建、验证关键信息不丢失。

## 2.37 Claude Code、OpenClaw 和 Hermes Agent 的上下文分别是如何拼接和组装的？各自的结构层次和设计哲学是什么？

三种 Agent 框架在上下文拼接上有截然不同的设计思路。理解它们如何"组装"上下文，有助于深入掌握 Agent 系统的架构设计权衡。

### 一、Claude Code：分层注入 + 渐进式压缩 + 自动恢复

Claude Code 的上下文组装是最精细的工程实践，核心是"分层注入"——每次模型调用前按层次精密拼接。

#### 1.1 上下文拼接结构

```text
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: 固定注入层 (走 Prefix Cache)                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ System Prompt (~4.2K tokens)                          │  │
│  │   - 角色定义、行为约束、安全规则                      │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ CLAUDE.md 文件层                                      │  │
│  │   - 项目级 CLAUDE.md (项目根目录)                     │  │
│  │   - 用户级 CLAUDE.md (~/.claude/)                     │  │
│  │   - 仅加载前 200 行 → 生成索引注入 System Prompt      │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ 环境信息                                              │  │
│  │   - 当前工作目录、Git 分支、操作系统                  │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ 工具描述 (延迟加载)                                   │  │
│  │   - Bash/Read/Write/Edit/Grep/Glob...                │  │
│  │   - MCP 工具 Schema（按需加载，非全量注入）            │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ Memory 文件                                           │  │
│  │   - MEMORY.md 索引列表（仅一行一行指针，非全文）      │  │
│  │   - 按需召回具体 memory 文件内容                      │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ Skill 描述                                            │  │
│  │   - 已激活的 Skill 说明文本                           │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  Layer 2: 条件注入层 (按需加载，不浪费 Token)                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 用户当前输入                                          │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ 文件读取结果 (用户 @ 引用的文件 / 工具读取的文件)     │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ 工具调用结果 (tool_call + tool_result 配对)           │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ 对话历史 (用户-助手-工具的多轮交互)                   │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  Layer 3: 压缩恢复层 (压缩后自动追回)                        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 最近读取的 5 个文件 (自动重新注入)                    │  │
│  │ 已激活的 Skills (自动重新注入)                        │  │
│  │ 当前任务的关键上下文                                  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

#### 1.2 Token 三档预警机制

```text
┌──────────────────────────────────────────────┐
│  70% 阈值 → 提示 (Advisory)                  │
│       └─ 日志记录，提醒 Agent 注意用量       │
│                                              │
│  85% 阈值 → 警告 (Warning)                   │
│       └─ 主动触发轻量级压缩                   │
│                                              │
│  90% 阈值 → 自动压缩 (Auto-compact)          │
│       └─ 执行不可逆上下文折叠                │
└──────────────────────────────────────────────┘
```

#### 1.3 CLAUDE.md 索引机制

```text
完整 CLAUDE.md 文件 (可能数千行)
        ↓
  只加载前 200 行
        ↓
  生成目录索引（h1/h2 标题列表）
        ↓
  注入 System Prompt 作为 memory 指针
        ↓
  Agent 需要时用 Read 工具按需获取具体章节
```

**设计效果**：不把整个 CLAUDE.md 塞进上下文，而是用"目录索引 + 按需读取"的方式，大幅节约 Token。

#### 1.4 压缩后自动恢复机制

这是 Claude Code 最关键的差异化设计——**压缩后不会"失忆"**：

```text
压缩执行前：
  工作集快照 → 记录当前读取的文件列表、激活的 Skills

压缩执行后：
  自动重新读取最近 5 个文件
  自动重新注入已激活的 Skills
  恢复当前任务上下文
```

**效果**：Agent 在压缩后仍能"记得"刚才在做什么文件、用什么工具，行为不会断裂。

#### 1.5 设计哲学

> "能不用 LLM 压缩就不用，优先用数学运算。分层注入，按需加载，压缩后自动恢复工作集。"

### 二、OpenClaw：文件引擎 + 可插拔上下文

OpenClaw 的上下文组装最开放——所有内容来自文件系统，上下文生命周期完全暴露给用户。

#### 2.1 上下文拼接结构

```text
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Bootstrap 启动层 (每文件上限 12,000 字符)         │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ AGENTS.md — Agent 行为规则和约束                      │  │
│  │ SOUL.md — Agent 身份定义、人格描述                    │  │
│  │ TOOLS.md — 工具使用说明（超限会截断）                 │  │
│  │ IDENTITY.md — 身份信息                                │  │
│  │ USER.md — 用户画像和偏好                              │  │
│  │ HEARTBEAT.md — 心跳/定时任务配置                      │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  Layer 2: 记忆注入层                                        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Memory 文件 (当日 + 昨日)                              │  │
│  │   - memory/YYYY-MM-DD.md (当日，append-only 日志)     │  │
│  │   - memory/YYYY-MM-(DD-1).md (昨日)                   │  │
│  │   - MEMORY.md (长期记忆，全量注入)                     │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ Active Recall 结果 (回复前子 Agent 检索注入)          │  │
│  │   - 关键词匹配 / 语义检索相关历史片段                 │  │
│  │   - 作为 untrusted context 注入底部                   │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  Layer 3: 工具与技能层                                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Skills 列表 (skill 名称 + 描述)                       │  │
│  │ 工具 Schema (JSON 格式)                               │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  Layer 4: 运行时层                                          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 当前用户输入                                          │  │
│  │ 对话历史                                              │  │
│  │ 工具调用与结果                                        │  │
│  │ 压缩后的摘要 (如有)                                   │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

#### 2.2 会话剪枝机制

```text
┌──────────────────────────────────────────────┐
│  1. 等待 Prompt Cache TTL 过期 (~5 分钟)     │
│     旧消息仍在缓存中，不急于裁剪              │
│                                              │
│  2. 对旧工具结果进行软裁剪                    │
│     裁剪掉过长的工具输出                      │
│                                              │
│  3. 硬清空                                    │
│     彻底删除指定轮次之前的所有消息            │
│                                              │
│  4. 对话文本保持不变                          │
│     只裁剪工具结果，不修改对话内容            │
└──────────────────────────────────────────────┘
```

#### 2.3 可替换 Context Engine

```text
默认引擎 (built-in)
        ↓ 用户可替换
自定义 Context Engine 插件
        ↓
用户完全控制：
  - 什么内容注入上下文
  - 什么时机触发压缩
  - 压缩后如何恢复
```

#### 2.4 设计哲学

> "文件即真理。所有长期状态必须持久化到 Markdown 文件。不是'把东西塞进上下文'，而是'把文件内容反映到上下文'。"

### 三、Hermes Agent：结构化交接 + 双层压缩

Hermes 的上下文组装最结构化——压缩产物不是泛泛的总结，而是给下一轮模型准备的"执行交接清单"。

#### 3.1 上下文拼接结构

```text
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Frozen Snapshot (Session 开始时冻结，中途不变)    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ System Prompt                                         │  │
│  │   - 角色定义 + 行为约束                               │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ MEMORY.md (2,200 字符硬上限)                          │  │
│  │   - 高密度声明式事实                                  │  │
│  │   - 例如："用户是 Python 后端开发者"                  │  │
│  │   - 超限触发 LLM 自主裁剪决策                         │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ USER.md (1,375 字符硬上限)                            │  │
│  │   - 用户认知画像                                      │  │
│  │   - 例如："技术栈: FastAPI + PostgreSQL"              │  │
│  └───────────────────────────────────────────────────────┘  │
│      ↑ Session 中途：新记忆只落盘，不改此快照              │
│                                                              │
│  Layer 2: 运行时注入层                                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 当前用户输入                                          │  │
│  │ 对话历史 (含工具调用)                                 │  │
│  │ 结构化摘要 (压缩产物，作为交接文档注入)               │  │
│  │ Session Search 结果 (FTS5 旁路召回的临时注入)         │  │
│  │ Nudge Engine 提醒                                     │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  Layer 3: 双层压缩体系                                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Gateway 层 (85% 阈值)                                 │  │
│  │   - 消息到达前预检，防 API 调用炸裂                   │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ Agent 循环层 (50% 阈值)                               │  │
│  │   - 主动低阈值触发，尽早释放空间                      │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

#### 3.2 结构化交接文档

压缩产物不是普通摘要，而是一份"可执行的交接清单"：

```text
┌──────────────────────────────────────────────┐
│ ## Goal                                      │
│ 用户的核心目标是什么                          │
│                                              │
│ ## Constraints & Preferences                 │
│ 有什么约束条件和偏好                          │
│                                              │
│ ## Progress                                  │
│ Done: 已完成的事项                            │
│ In Progress: 正在进行的事项                   │
│ Blocked: 被阻塞的事项                         │
│                                              │
│ ## Key Decisions                             │
│ 关键决策及其理由                              │
│                                              │
│ ## Relevant Files                            │
│ 涉及的文件路径                                │
│                                              │
│ ## Next Steps                                │
│ 下一步要做什么                                │
│                                              │
│ ## Critical Context                          │
│ 其他必须保留的关键上下文                      │
└──────────────────────────────────────────────┘
```

**增量更新机制**：多次压缩在上一次摘要的基础上追加，而非每次重建。这样信息递进保持，不会在压缩中丢失历史。

#### 3.3 Memory + Skill 分离

```text
MEMORY.md (2,200 字符)
  → 声明式事实："用户偏好 XX"
  → 常驻 System Prompt

USER.md (1,375 字符)
  → 用户认知："技术栈: XX"
  → 常驻 System Prompt

Skills (Markdown 文件)
  → 过程性记忆 / 可复用能力
  → 按需注入，非全量
```

#### 3.4 设计哲学

> "压缩不是泛泛而谈的总结，而是给下一轮模型准备一份可继续执行的交接清单。把常驻记忆做小，把历史召回放旁路，强调稳定前缀。"

### 四、三者核心差异对比

| 维度             | Claude Code                                                         | OpenClaw                                                    | Hermes Agent                                            |
| ---------------- | ------------------------------------------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------- |
| **拼接方式**     | 分层注入（固定层+条件层+恢复层）                                    | 文件列表 + 插件引擎                                         | 冻结快照 + 运行时注入                                   |
| **固定注入层**   | System Prompt + CLAUDE.md 索引 + 环境 + 工具 + Memory 指针 + Skills | Bootstrap 文件（AGENTS/SOUL/TOOLS/IDENTITY/USER/HEARTBEAT） | System Prompt + MEMORY.md(2200字符) + USER.md(1375字符) |
| **条件注入层**   | 用户输入 + 文件读取 + 工具结果 + 对话历史                           | Active Recall 结果 + 对话历史 + 工具结果                    | 用户输入 + 对话历史 + 结构化摘要 + Session Search       |
| **压缩恢复**     | 自动恢复最近5文件 + Skills（关键差异化）                            | Memory Flush 抢救 + 依赖文件系统恢复                        | 增量摘要递进保持                                        |
| **Token 预警**   | 三档：70%/85%/90%                                                   | 缓存 TTL + 软剪枝/硬清空                                    | 双层：Gateway 85% + Agent 50%                           |
| **压缩策略**     | 5 级级联（优先数学运算，不用 LLM）                                  | 4 级（Snip→Microcompact→Collapse→Autocompact）              | 4 Phase 结构化（删除旧输出→边界计算→结构化摘要→组装）   |
| **Memory 注入**  | 仅注入索引（一行一行指针），按需召回                                | 全量注入当日+昨日日志 + MEMORY.md                           | 硬上限常驻 + FTS5 按需旁路召回                          |
| **前缀缓存优化** | 走 Prefix Cache（固定层不变）                                       | 不特别优化                                                  | Frozen Snapshot 专门优化                                |
| **核心痛点**     | 200行索引上限，无语义搜索                                           | 文件膨胀，"数字囤积症"                                      | 硬上限可能丢失低频但重要的信息                          |

### 五、知识扩展

- **上下文裁剪与压缩（2.36 节）**：本节的压缩策略是具体实现手段，2.36 节详细讨论了裁剪和压缩的通用方法及 Prompt 设计。
- **OpenClaw 和 Hermes 的上下文管理机制（2.35 节）**：2.35 节侧重管理策略和设计哲学，本节侧重具体的拼接结构和层次，二者互补。
- **Prompt Caching 原理**：Hermes 的 Frozen Snapshot 和 Claude Code 的固定注入层都利用了 Prompt Caching，理解 Caching 原理有助于理解为什么要区分"固定层"和"条件层"。
- **SubAgent 上下文隔离**：Claude Code 的子 Agent 使用 minimal promptMode 时，上下文拼接完全不同——仅注入任务描述和关键参数，不包含父 Agent 对话历史。
- **Token 计数与上下文监控**：三者的预警机制都依赖精确的 Token 计数，理解 Token 计数的底层实现有助于理解预警阈值的设置依据。
- **多 Agent 上下文传递**：在多 Agent 协作中，上下文如何拼接从一个 Agent 传递给另一个 Agent，是比单 Agent 更复杂的问题。
- **Lost in the Middle 问题**：三者不同的上下文拼接方式，对"Lost in the Middle"（中间信息被忽略）问题有不同的缓解效果。

### 完整口头回答

三种框架在上下文拼接上有截然不同的设计。

Claude Code 采用分层注入结构。最底层是固定注入层——System Prompt、CLAUDE.md 索引（只取前 200 行生成目录索引，不塞全文）、环境信息、工具 Schema、Memory 指针列表、Skill 描述，这层走 Prefix Cache 不变。中间是条件注入层——用户输入、文件读取结果、工具调用结果、对话历史，按需加载。顶部是压缩恢复层——压缩后自动重新注入最近读取的 5 个文件和已激活的 Skills，这是它"不容易失忆"的关键。Token 预警采用三档机制：70% 提示、85% 警告触发轻量压缩、90% 自动执行不可逆压缩。设计哲学是"能不用 LLM 压缩就不用，优先数学运算，分层注入，压缩后自动恢复工作集"。

OpenClaw 采用文件引擎结构。Bootstrap 层从文件系统加载——AGENTS.md、SOUL.md、TOOLS.md、IDENTITY.md、USER.md、HEARTBEAT.md，每个文件上限 12,000 字符。记忆注入层包括当日+昨日的 append-only 日志和 MEMORY.md 全量注入，以及 Active Recall 子 Agent 检索结果作为 untrusted context 注入。工具 Schema 和 Skills 列表直接计入上下文。上下文引擎可插拔，用户可以完全自定义。压缩策略是等待缓存 TTL 过期、软裁剪工具输出、硬清空。设计哲学是"文件即真理，所有长期状态必须持久化"。

Hermes Agent 采用冻结快照 + 结构化交接结构。Frozen Snapshot 层在 Session 开始时创建——System Prompt + MEMORY.md（2200 字符硬上限）+ USER.md（1375 字符硬上限），Session 中途新记忆只落盘不修改快照，保证前缀缓存稳定。运行时注入层包括用户输入、对话历史、结构化摘要（作为交接文档）、Session Search 结果、Nudge 提醒。双层压缩体系——Gateway 层 85% 阈值预检，Agent 循环层 50% 阈值主动低阈值触发。设计哲学是"压缩不是泛泛的总结，而是给下一轮模型准备可继续执行的交接清单"。

核心差异在于压缩后的恢复策略：Claude Code 自动恢复工作集（文件+Skills），OpenClaw 依赖文件系统，Hermes Agent 用增量摘要递进保持。这也是 Claude Code "不容易失忆"的关键工程优势。

## 2.38 在工程化部署一个 Agent 时，需要考虑哪些核心问题？从基础设施、可靠性、性能、安全等维度该如何系统规划？

工程化部署 Agent 远比部署一个普通 API 服务复杂——Agent 是有状态的、多步推理的、调用外部工具的，需要考虑的问题维度远超传统的微服务部署。

### 一、基础设施与架构设计

#### 1.1 部署架构选择

```text
┌─────────────────────────────────────────────────────────────┐
│                  Agent 部署架构层次                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [入口层]                                                    │
│    ├─ API Gateway (认证/限流/路由)                           │
│    ├─ WebSocket Server (实时 SSE 流式推送)                   │
│    └─ Load Balancer (多实例分发)                             │
│         ↓                                                   │
│  [编排层]                                                    │
│    ├─ Agent Orchestrator (Agent 循环调度)                    │
│    ├─ Task Queue (任务排队与优先级)                          │
│    └─ Session Manager (会话状态维护)                         │
│         ↓                                                   │
│  [推理层]                                                    │
│    ├─ LLM API Proxy (多模型路由/故障转移)                    │
│    ├─ Model Pool (不同模型的热备实例)                        │
│    └─ Token 配额管理                                        │
│         ↓                                                   │
│  [工具层]                                                    │
│    ├─ Tool Executor (沙箱执行环境)                           │
│    ├─ Tool Registry (工具的注册/发现/版本管理)               │
│    └─ MCP Server Cluster (工具服务化)                        │
│         ↓                                                   │
│  [存储层]                                                    │
│    ├─ Session Store (Redis/PostgreSQL)                      │
│    ├─ Memory Store (向量数据库 + 全文检索)                   │
│    └─ Log/Trace Store (OpenTelemetry + ClickHouse)          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 1.2 关键技术选型

| 层次         | 技术选项                                    | 考虑因素                       |
| ------------ | ------------------------------------------- | ------------------------------ |
| **容器编排** | Kubernetes / Docker Compose / Nomad         | 规模、运维复杂度、云平台绑定   |
| **消息队列** | Redis Streams / Kafka / RabbitMQ            | 延迟要求、持久化需求、吞吐量   |
| **会话存储** | Redis (热数据) + PostgreSQL (冷数据)        | 延迟、持久性、查询能力         |
| **向量存储** | Milvus (独立部署) / pgvector (与业务库合一) | 规模、运维成本、查询延迟       |
| **LLM 网关** | LiteLLM / 自研 Proxy / OpenRouter           | 多模型切换、成本控制、故障转移 |
| **监控体系** | OpenTelemetry + Grafana + Prometheus        | 链路追踪、指标聚合、告警       |

#### 1.3 多环境策略

```text
开发环境 (Dev)     → 沙箱环境 (Sandbox)  → 预发布 (Staging)  → 生产 (Production)
  │                    │                     │                   │
  ├─ Mock LLM          ├─ 真实 LLM           ├─ 生产镜像          ├─ 全量真实服务
  ├─ 本地 Docker       ├─ 隔离的工具环境     ├─ 影子流量回放       ├─ 灰度/金丝雀发布
  └─ 快速迭代          └─ 功能验证           └─ 性能压测          └─ 全量监控
```

**关键实践**：
- 沙箱环境使用**与生产隔离的工具实例**（独立的数据库、文件系统），防止 Agent 误操作破坏生产数据
- 预发布阶段进行**影子流量回放**：将生产流量复制一份到 Staging，对比新旧版本输出差异
- 生产采用**金丝雀发布**：先切 5% 流量到新版本，观察 30 分钟无异常再全量

### 二、可靠性与容错

#### 2.1 Agent 特有的故障模式

| 故障类型         | 表现                   | 根因                    | 发生概率 |
| ---------------- | ---------------------- | ----------------------- | -------- |
| **LLM 调用超时** | Agent 循环卡住         | API 限流 / 模型服务过载 | 高       |
| **工具执行失败** | 某个工具返回错误       | 参数错误 / 外部服务故障 | 中       |
| **无限循环**     | Agent 反复执行相同操作 | 规划错误 / LLM 判断失误 | 中       |
| **上下文溢出**   | 超过窗口限制           | 对话过长 / 工具输出过大 | 高       |
| **资源泄漏**     | 子进程/临时文件未清理  | 工具执行异常退出        | 低       |
| **状态不一致**   | 会话状态与实际不符     | 并发写入 / 网络分区     | 低       |

#### 2.2 容错机制设计

```text
┌─────────────────────────────────────────────────────────────┐
│                    多层容错体系                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  第一层：超时控制                                            │
│    ├─ LLM API 调用超时：30s (可配置)                         │
│    ├─ 单次工具执行超时：60s                                  │
│    ├─ 总 Agent 循环超时：300s (5 分钟)                       │
│    └─ 超时策略：重试 (最多 3 次) → 降级 → 告知用户          │
│                                                             │
│  第二层：熔断降级                                            │
│    ├─ LLM 服务错误率 > 50% → 熔断 30s → 切换到备用模型      │
│    ├─ 工具连续失败 > 3 次 → 跳过该工具 → 用替代方案          │
│    └─ 上下文使用率 > 90% → 触发压缩 → 仍不足则截断           │
│                                                             │
│  第三层：兜底回复                                            │
│    ├─ LLM 完全不可用 → 返回预设的错误提示                    │
│    ├─ 工具不可用 → 告知用户当前哪些功能受限                  │
│    └─ 系统过载 → 返回"系统繁忙，请稍后重试"                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2.3 无限循环防护

Agent 在多步推理中可能陷入"执行→失败→重试→再失败"的死循环：

```python
class LoopDetector:
    """Agent 循环检测器"""

    def __init__(
        self,
        max_iterations: int = 50,          # 最大迭代次数
        max_repeated_actions: int = 3,     # 连续相同操作上限
        action_similarity_threshold: float = 0.85,
    ):
        self.max_iterations = max_iterations
        self.max_repeated_actions = max_repeated_actions
        self.action_similarity_threshold = action_similarity_threshold
        self.action_history: list[dict] = []

    def check(self, iteration: int, action: dict) -> bool:
        """
        检查是否陷入循环。返回 True 表示需要中断。

        检测规则：
        1. 总迭代次数超过上限
        2. 连续 3 次执行相同工具 + 相同参数
        3. 最近 5 次操作中有 4 次是同一工具
        """
        # 规则 1: 迭代次数上限
        if iteration >= self.max_iterations:
            return True

        # 记录当前操作
        self.action_history.append({
            "tool": action.get("tool"),
            "args_hash": hash(str(action.get("args", {}))),
            "iteration": iteration,
        })

        # 规则 2: 连续相同操作
        if len(self.action_history) >= self.max_repeated_actions:
            recent = self.action_history[-self.max_repeated_actions:]
            if all(
                r["tool"] == recent[0]["tool"]
                and r["args_hash"] == recent[0]["args_hash"]
                for r in recent
            ):
                return True

        # 规则 3: 高频同一工具
        if len(self.action_history) >= 5:
            recent_5 = self.action_history[-5:]
            tool_counts = {}
            for r in recent_5:
                tool_counts[r["tool"]] = tool_counts.get(r["tool"], 0) + 1
            if max(tool_counts.values()) >= 4:
                return True

        return False

    def get_intervention_hint(self) -> str:
        """生成中断提示"""
        recent_tools = [a["tool"] for a in self.action_history[-5:]]
        return (
            f"检测到潜在循环：最近操作序列为 {recent_tools}。"
            f"请总结当前已完成的工作，明确下一步方向。"
            f"如果多次尝试同一操作均失败，请更换方案或请求用户协助。"
        )
```

#### 2.4 状态恢复机制

Agent 崩溃或重启后需要能够恢复会话状态：

```text
状态恢复策略：

1. 会话状态持久化（每次 Agent 循环结束时写入）：
   ├─ 对话历史 (messages)
   ├─ 当前任务上下文 (current_task)
   ├─ 已完成步骤列表 (completed_steps)
   └─ 待办步骤列表 (pending_steps)

2. 恢复流程：
   ├─ 加载上次持久化的会话状态
   ├─ 注入恢复提示：[系统消息] Agent 在上次会话中意外中断，
   │   以下是中断前的状态摘要...
   ├─ Agent 根据摘要继续未完成的任务
   └─ 如无法恢复（状态损坏），降级为重新开始
```

### 三、性能优化

#### 3.1 关键性能指标

| 指标                                 | 定义                                  | 目标值                      | 测量方法            |
| ------------------------------------ | ------------------------------------- | --------------------------- | ------------------- |
| **TTFR** (Time to First Response)    | 用户发送消息到看到第一个 Token 的延迟 | < 1s                        | SSE 流首 Token 时间 |
| **TTCR** (Time to Complete Response) | 完整回复的端到端延迟                  | < 10s (简单) / < 60s (复杂) | 请求-完整响应时间   |
| **Throughput**                       | 并发处理的任务数                      | 根据实例规模                | 单位时间完成任务数  |
| **Token Efficiency**                 | 完成任务的平均 Token 消耗             | 持续优化                    | 单任务 Token 用量   |
| **Cache Hit Rate**                   | Prompt Caching 前缀命中率             | > 80%                       | 缓存命中/总请求     |

#### 3.2 优化策略

```text
┌─────────────────────────────────────────────────────────────┐
│                    性能优化策略                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  推理层优化：                                                │
│    ├─ Prompt Caching：固定 System Prompt 走缓存              │
│    ├─ 推测解码：小模型预生成，大模型验证                     │
│    ├─ 批处理：同类请求合并批处理（降低 API 调用频次）        │
│    └─ 模型分级：简单任务用小模型，复杂任务用大模型           │
│                                                             │
│  工具层优化：                                                │
│    ├─ 工具预热：常驻工具进程池，避免冷启动                   │
│    ├─ 并行工具调用：无依赖的工具并发执行                     │
│    ├─ 结果缓存：相同工具+相同参数的查询结果缓存              │
│    └─ 超时熔断：慢工具不阻塞 Agent 主循环                    │
│                                                             │
│  系统层优化：                                                │
│    ├─ 连接池：复用 HTTP/数据库连接                           │
│    ├─ 异步 I/O：asyncio 异步处理所有外部调用                 │
│    └─ 内存管理：限制单 Agent 实例的内存上限                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 3.3 并发与隔离

```text
并发模型选择：

方案 A: 每会话一个 Agent 实例（进程级隔离）
  优点：完全隔离，一个会话崩溃不影响其他
  缺点：资源开销大，不适合大规模并发
  适用：企业级、任务关键型

方案 B: 协程级并发（asyncio）
  优点：资源开销小，支持高并发
  缺点：隔离性弱，共享内存污染风险
  适用：高并发、任务轻量型

方案 C: 混合模式
  每个 Pod 运行 N 个 Worker 进程 × M 个协程
  进程隔离 + 协程并发 = 兼顾安全与效率
```

### 四、安全与权限管理

#### 4.1 安全威胁模型

```text
┌─────────────────────────────────────────────────────────────┐
│                  Agent 安全威胁全景                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [输入层威胁]                                                │
│    ├─ Prompt Injection: 用户输入中注入恶意指令               │
│    ├─ 数据投毒: 污染检索库或工具输入                         │
│    └─ 越狱攻击: 绕过安全限制获取危险能力                     │
│                                                             │
│  [工具层威胁]                                                │
│    ├─ 权限提升: Agent 调用超出授权范围的工具                 │
│    ├─ 命令注入: 工具参数中包含恶意 Shell 命令                │
│    └─ 数据泄漏: 工具输出中暴露敏感信息                       │
│                                                             │
│  [输出层威胁]                                                │
│    ├─ 有害内容生成: 生成违规文本或代码                       │
│    ├─ PII 泄漏: 回复中包含用户隐私数据                       │
│    └─ 幻觉误导: 生成看似合理但错误的危险建议                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 4.2 最小权限原则

```python
class ToolPermission:
    """工具权限——最小权限原则"""

    # 权限级别定义
    READ_ONLY = "read_only"      # 只读：查看文件、查询数据库
    READ_WRITE = "read_write"    # 读写：修改文件、写入数据库
    EXECUTE = "execute"          # 执行：运行命令、调用外部 API
    ADMIN = "admin"              # 管理：修改配置、管理用户
    DANGEROUS = "dangerous"      # 危险：删除、格式化、发送请求


# 每个工具必须声明所需权限级别
TOOL_PERMISSIONS = {
    "read_file":   ToolPermission.READ_ONLY,
    "list_dir":    ToolPermission.READ_ONLY,
    "search_db":   ToolPermission.READ_ONLY,
    "write_file":  ToolPermission.READ_WRITE,
    "update_db":   ToolPermission.READ_WRITE,
    "run_bash":    ToolPermission.EXECUTE,
    "deploy_app":  ToolPermission.EXECUTE,
    "send_email":  ToolPermission.DANGEROUS,
    "delete_file": ToolPermission.DANGEROUS,
}


class PermissionGate:
    """权限门控：在工具调用前检查权限"""

    def __init__(self, user_role: str):
        # 角色 → 允许的最高权限
        self.role_permissions = {
            "viewer":  {ToolPermission.READ_ONLY},
            "editor":  {ToolPermission.READ_ONLY,
                        ToolPermission.READ_WRITE},
            "developer": {ToolPermission.READ_ONLY,
                          ToolPermission.READ_WRITE,
                          ToolPermission.EXECUTE},
            "admin":   {ToolPermission.READ_ONLY,
                        ToolPermission.READ_WRITE,
                        ToolPermission.EXECUTE,
                        ToolPermission.ADMIN,
                        ToolPermission.DANGEROUS},
        }
        self.allowed = self.role_permissions.get(user_role, set())

    def check(self, tool_name: str) -> bool:
        """检查用户是否有权限调用该工具"""
        required = TOOL_PERMISSIONS.get(tool_name)
        if required is None:
            return False  # 未知工具拒绝调用

        if required in self.allowed:
            return True

        # 危险操作需要二次确认
        if required == ToolPermission.DANGEROUS:
            return self._require_confirmation(tool_name)

        return False

    def _require_confirmation(self, tool_name: str) -> bool:
        """危险操作需要用户二次确认"""
        # 实际实现：发送确认请求，等待用户回复
        return False  # 默认拒绝
```

#### 4.3 审计与合规

```text
审计日志记录内容：
  ├─ 谁 (user_id, session_id)
  ├─ 何时 (timestamp, duration)
  ├─ 做了什么 (tool_calls, their_args, their_results)
  ├─ LLM 推理链 (thought_process, reasoning_steps)
  ├─ 上下文快照 (compressed_context_snapshot)
  └─ 结果 (task_completed, error_info)

合规要求：
  ├─ 数据保留策略：日志保留 90 天，可配置
  ├─ 数据脱敏：PII (手机号/身份证/邮箱) 自动脱敏后存储
  ├─ 访问控制：审计日志仅管理员可查
  └─ 合规标准：SOC2 / GDPR / 等保
```

### 五、可观测性

#### 5.1 四维监控体系

```text
┌─────────────────────────────────────────────────────────────┐
│                   Agent 四维监控体系                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [延迟维度]                       [质量维度]                 │
│    ├─ LLM 推理延迟                   ├─ 任务成功率           │
│    ├─ 工具执行延迟                   ├─ 用户满意度评分       │
│    ├─ Agent 循环总延迟               ├─ 工具调用准确率       │
│    └─ 首 Token 延迟 (TTFR)          └─ Token 效率           │
│                                                             │
│  [吞吐维度]                       [资源维度]                 │
│    ├─ 并发会话数                     ├─ GPU 利用率           │
│    ├─ 单位时间完成任务数             ├─ Token 消耗量/速率    │
│    ├─ API 调用 QPS                   ├─ 内存/显存使用率      │
│    └─ 消息吞吐量                     └─ 磁盘 I/O             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 5.2 链路追踪

Agent 的调用链路比普通服务复杂得多：

```text
一个典型的 Agent 请求链路：
用户消息 → API Gateway → Agent Orchestrator → LLM API (第 1 轮推理)
  → Tool: read_file → Tool: search_code → LLM API (第 2 轮推理)
  → Tool: write_file → LLM API (第 3 轮推理) → 返回结果

需要追踪的信息：
  ├─ trace_id: 贯穿整个 Agent 调用的唯一标识
  ├─ span_id: 每次 LLM 调用 / 工具调用为一个 span
  ├─ parent_span_id: 上一层的 span
  └─ 每个 span 记录: 输入、输出、耗时、状态、Token 消耗
```

### 六、成本控制

#### 6.1 成本构成

| 成本类型              | 占比 (典型) | 优化方向                             |
| --------------------- | ----------- | ------------------------------------ |
| LLM API Token 费用    | 60-80%      | Prompt Caching、模型分级、上下文压缩 |
| GPU/算力费用 (自部署) | 10-30%      | 量化、批处理、动态扩缩容             |
| 基础设施费用          | 5-10%       | 合理配置、Spot 实例                  |
| 存储费用              | 2-5%        | 数据生命周期管理                     |

#### 6.2 Token 成本优化

```text
优化手段                     预期节省
Prompt Caching              30-50%（前缀命中场景）
上下文压缩/裁剪             20-40%
小模型处理简单任务          50-70%（简单任务占比高时）
工具输出截断                10-20%
精简 System Prompt          5-15%
```

### 七、知识扩展

- **Agent 任务阻塞治理（2.33 节）**：本节侧重全生命周期部署规划，2.33 节侧重生产问题定位，二者互补。
- **上下文裁剪与压缩（2.36 节）**：性能优化和成本控制的核心手段，工程部署中需要将压缩策略作为基础设施的一部分。
- **SubAgent 机制（2.34 节）**：并发部署中，子 Agent 的 promptMode 选择直接影响 Token 消耗和延迟。
- **LLM 网关**：LiteLLM、OpenRouter 等多模型网关是工程部署中统一管理多模型调用的关键组件。
- **MCP 协议**：工具服务化的标准协议，工程部署中将工具作为 MCP Server 集群管理。
- **CI/CD for Agent**：Agent 的持续集成与普通服务不同——需要包含 LLM 行为回归测试（eval set），每次 Prompt 变更都需要跑 eval。
- **多租户隔离**：SaaS 场景下不同租户的会话、记忆、工具调用需要严格隔离。

### 完整口头回答

在工程化部署一个 Agent 时，需要从基础设施、可靠性、性能、安全、可观测性、成本控制六个维度系统规划。

基础设施层面，需要设计五层部署架构：入口层（API Gateway + WebSocket + 负载均衡）、编排层（Agent Orchestrator + 任务队列 + 会话管理）、推理层（LLM API Proxy + 多模型路由）、工具层（Tool Executor 沙箱 + MCP Server 集群）、存储层（Redis 会话 + 向量数据库 + 日志）。还需要配置开发→沙箱→预发布→生产的多环境流水线，以及金丝雀发布策略。

可靠性层面，Agent 有六种特有的故障模式：LLM 超时、工具执行失败、无限循环、上下文溢出、资源泄漏、状态不一致。需要建立三层容错体系：超时控制（LLM 调用 30s/工具 60s/总循环 300s）、熔断降级（错误率 > 50% 自动切换备用模型）、兜底回复。无限循环是最隐蔽的故障，需要通过迭代次数上限、连续重复操作检测、高频同一工具检测三道防线来防护。还需要持久化会话状态，支持崩溃后恢复。

性能层面，核心指标包括 TTFR（首 Token 延迟 < 1s）、TTCR（完整响应 < 10s）、Token 效率、Cache 命中率。优化策略包括 Prompt Caching、工具预热与并行调用、模型分级（简单任务用小模型）。并发模型采用混合模式——进程隔离 + 协程并发，兼顾安全与效率。

安全层面，需要防御输入层（Prompt 注入、越狱）、工具层（权限提升、命令注入、数据泄漏）、输出层（有害内容、PII 泄漏）三类威胁。实施最小权限原则——每个工具声明所需权限级别，通过权限门控在调用前检查。

可观测性层面，建立四维监控（延迟/质量/吞吐/资源）加上全链路追踪（trace_id 贯穿所有 LLM 调用和工具调用）。成本控制层面，Token 费用占 60-80%，通过 Prompt Caching、上下文压缩、模型分级等手段可节省 30-50%。

## 2.39 如果设计一个多智能体协作系统，如何规划 Agent 之间的通信机制和任务分配策略？

多智能体协作系统 (Multi-Agent Collaboration System) 的核心是两个问题：**Agent 之间如何通信**（传递什么信息、用什么格式、通过什么通道），以及**任务如何分配**（谁来干什么、如何协调、如何处理冲突）。

### 一、通信机制设计

#### 1.1 通信架构模式

```text
┌─────────────────────────────────────────────────────────────┐
│                 三种通信架构模式                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  模式 A: 星型 (Hub-Spoke)                                   │
│                                                             │
│              ┌───────┐                                      │
│              │Orchestrator│  ← 中心调度者                    │
│              └─┬──┬──┬┘                                     │
│                │  │  │                                      │
│           ┌────┘  │  └────┐                                 │
│        Agent1  Agent2  Agent3                               │
│                                                             │
│  优点：结构简单，易于理解和调试                              │
│  缺点：Orchestrator 成为单点瓶颈和故障点                     │
│  适用：任务有明确的串行/并行依赖关系                        │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  模式 B: 网状 (P2P / Mesh)                                  │
│                                                             │
│           Agent1 ──────── Agent2                            │
│               │ \         / │                               │
│               │  \       /  │                               │
│               │   \     /   │                               │
│               │    \   /    │                               │
│           Agent3 ──────── Agent4                            │
│                                                             │
│  优点：灵活，无单点瓶颈，Agent 间直接沟通                    │
│  缺点：拓扑复杂，消息可能爆炸 (O(n²) 通道)                  │
│  适用：去中心化的协作场景，Agent 关系对等                    │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  模式 C: 混合型 (Hierarchical + Pub/Sub)                     │
│                                                             │
│              ┌──────────────────┐                           │
│              │  消息总线 (Bus)   │  ← 共享通信基础设施       │
│              └──┬──┬──┬──┬───┬┘                             │
│                 │  │  │  │   │                               │
│           Team Lead  │  │  Team Lead                         │
│             /  \     │  │    /  \                            │
│          Agent Agent  │  │ Agent Agent                       │
│                       │  │                                   │
│                   Specialist Specialist                      │
│                                                             │
│  优点：兼顾灵活性和可管理性，支持分组和广播                  │
│  缺点：需要额外的消息总线基础设施                           │
│  适用：大规模、异构的多 Agent 系统                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 1.2 通信内容设计

Agent 之间通信的消息应该结构化，包含以下要素：

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time
import uuid


class MessageType(Enum):
    TASK_ASSIGN = "task_assign"         # 任务分配
    TASK_RESULT = "task_result"         # 任务结果
    QUERY = "query"                     # 向其他 Agent 查询信息
    RESPONSE = "response"               # 回复查询
    BROADCAST = "broadcast"             # 广播通知
    HEARTBEAT = "heartbeat"             # 心跳
    HANDOFF = "handoff"                 # 任务移交
    CONFLICT = "conflict"               # 冲突通知
    AGREEMENT = "agreement"             # 达成共识


class MessagePriority(Enum):
    CRITICAL = 1    # 关键：阻塞性消息，必须立即处理
    HIGH = 2        # 高：影响任务进度
    NORMAL = 3      # 普通：常规通信
    LOW = 4         # 低：通知、日志等


@dataclass
class AgentMessage:
    """Agent 间通信消息的标准格式"""
    # 元信息
    message_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    sender_id: str = ""
    receiver_id: str = ""  # 空字符串表示广播
    conversation_id: str = ""  # 关联的对话 ID

    # 消息内容
    msg_type: MessageType = MessageType.QUERY
    priority: MessagePriority = MessagePriority.NORMAL
    subject: str = ""          # 消息主题（一句话概括）
    content: dict = field(default_factory=dict)  # 结构化内容

    # 任务上下文
    task_id: Optional[str] = None
    parent_task_id: Optional[str] = None  # 父任务 ID
    context_refs: list[str] = field(default_factory=list)  # 引用的上下文 ID

    # 期望的回复
    expect_reply: bool = True
    reply_timeout: float = 30.0  # 等待回复的超时秒数

    # 元数据
    timestamp: float = field(default_factory=time.time)
    ttl: int = 10  # 消息生存时间（跳数）

    def to_prompt_context(self) -> str:
        """将消息转换为可注入上下文的文本"""
        return f"""[Agent Message]
From: {self.sender_id}
To: {self.receiver_id or 'All'}
Type: {self.msg_type.value}
Priority: {self.priority.name}
Subject: {self.subject}
Content: {self.content}
Context: {self.context_refs}
"""
```

#### 1.3 通信协议选型

| 协议                             | 模式             | 延迟 | 适用场景                  | 优缺点                            |
| -------------------------------- | ---------------- | ---- | ------------------------- | --------------------------------- |
| **A2A (Agent-to-Agent)**         | 标准化 JSON 消息 | 中   | 跨框架、跨平台 Agent 协作 | Google 标准，支持 Agent Card 发现 |
| **MCP (Model Context Protocol)** | 工具调用         | 低   | Agent 调用外部工具/服务   | Anthropic 主导，偏工具层          |
| **gRPC**                         | 二进制 RPC       | 极低 | 同集群内部高性能通信      | 高性能，强类型，需预定义接口      |
| **Redis Pub/Sub**                | 发布-订阅        | 低   | 轻量级消息广播            | 简单，无持久化保障                |
| **Kafka**                        | 事件流           | 中   | 大规模异步消息            | 高吞吐，持久化，支持重放          |
| **NATS**                         | 消息队列         | 极低 | 云原生微服务通信          | 极轻量，支持请求-回复模式         |
| **WebSocket**                    | 全双工           | 低   | 实时双向通信              | 适合需要实时推送的场景            |

**选型原则**：
- **同进程/同 Pod**：直接函数调用
- **同集群**：gRPC / NATS
- **跨集群/跨平台**：A2A 协议 + Kafka
- **轻量广播**：Redis Pub/Sub
- **外部工具调用**：MCP 协议

#### 1.4 上下文传递策略

Agent 间通信的核心难题之一是**上下文传递**——接收方需要多少上下文才能正确理解消息和完成任务：

```text
策略 A: 最小上下文 (Minimal Context)
  仅传递消息本身（任务描述 + 关键参数），不附带发送方的对话历史
  优点：Token 消耗小，接收方推理聚焦
  缺点：缺少背景可能造成理解偏差
  适用：独立性强的原子任务

策略 B: 共享上下文 (Shared Context)
  所有 Agent 共享同一个上下文空间（共享的向量数据库 / 知识图谱）
  优点：信息一致性好，避免信息孤岛
  缺点：需要额外的共享基础设施，上下文可能过大
  适用：需要紧密协作的任务

策略 C: 选择性上下文 (Selective Context)
  发送方根据接收方的角色和任务，有选择地传递相关上下文
  优点：在信息完整性和 Token 效率间取得平衡
  缺点：需要发送方有能力判断哪些上下文对接收方有用
  适用：一般情况（推荐）
```

### 二、任务分配策略

#### 2.1 任务分解方法

```text
┌─────────────────────────────────────────────────────────────┐
│                    任务分解方法                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  方法一：声明式分解 (Dependency-Based)                       │
│    输入：用户目标 + 任务描述                                 │
│    输出：DAG (有向无环图) 任务依赖树                         │
│                                                             │
│    示例：用户请求"从零搭建一个 Web 应用并部署"              │
│                                                             │
│    [需求分析] ─────────────┐                                │
│         ↓                  ↓                                │
│    [技术选型]          [UI 设计]                             │
│         ↓                  ↓                                │
│    [后端开发] ←──────── [前端开发]                           │
│         ↓                  ↓                                │
│    [集成测试] ←────────────┘                                │
│         ↓                                                   │
│    [部署上线]                                                │
│                                                             │
│  方法二：动态分解 (LLM-Driven)                                │
│    Orchestrator 接收任务 → LLM 分析分解 → 分配子 Agent      │
│    优点：灵活性高，适应未知任务                              │
│    缺点：分解质量依赖 LLM 能力                               │
│                                                             │
│  方法三：模板匹配 (Template-Based)                           │
│    预定义常见任务的分解模板                                  │
│    优点：稳定可靠，适合已知任务                              │
│    缺点：不适用于全新类型的任务                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2.2 Agent 角色与能力注册

```python
from dataclasses import dataclass


@dataclass
class AgentCapability:
    """Agent 能力声明"""
    agent_id: str
    agent_type: str           # planner / executor / reviewer / tool
    skills: list[str]         # 技能标签：["python", "react", "devops"]
    expertise_level: int      # 专精程度 1-10
    max_concurrent_tasks: int # 最大并行任务数
    preferred_task_types: list[str]  # 偏好任务类型
    tool_set: list[str]       # 可用的工具列表
    context_limit: int        # 上下文窗口大小


class AgentRegistry:
    """Agent 注册中心——能力发现的基础"""

    def __init__(self):
        self.agents: dict[str, AgentCapability] = {}

    def register(self, capability: AgentCapability):
        self.agents[capability.agent_id] = capability

    def unregister(self, agent_id: str):
        self.agents.pop(agent_id, None)

    def find_best_match(
        self,
        required_skills: list[str],
        task_type: str,
    ) -> list[AgentCapability]:
        """根据任务需求找到最匹配的 Agent"""
        scored = []
        for agent in self.agents.values():
            # 技能匹配度
            skill_match = len(
                set(required_skills) & set(agent.skills)
            ) / max(len(required_skills), 1)

            # 任务类型匹配
            type_match = 1.0 if task_type in agent.preferred_task_types else 0.5

            # 负载因子（并发任务越少，可用度越高）
            load_factor = 1.0

            # 综合得分
            score = skill_match * 0.5 + type_match * 0.3 + load_factor * 0.2
            scored.append((score, agent))

        # 按得分降序排列
        scored.sort(key=lambda x: x[0], reverse=True)
        return [agent for _, agent in scored]
```

#### 2.3 任务分配算法

```text
┌─────────────────────────────────────────────────────────────┐
│                    任务分配算法                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  算法一：能力最优匹配 (Best-Fit)                              │
│    for 每个待分配的子任务:                                    │
│        找到技能匹配度最高且当前负载最低的 Agent               │
│        分配给该 Agent                                       │
│    适用：Agent 能力有明确差异的异构系统                      │
│                                                             │
│  算法二：负载均衡 (Round-Robin / Least-Connection)            │
│    按轮询或当前负载分配，确保各 Agent 负载均衡               │
│    适用：Agent 能力同构的系统                                │
│                                                             │
│  算法三：拍卖/竞标 (Auction/Bidding)                         │
│    1. Orchestrator 广播子任务到所有相关 Agent                │
│    2. 各 Agent 根据自身能力、负载、兴趣返回"竞标分数"       │
│    3. Orchestrator 选择出价最优的 Agent                       │
│    优点：去中心化决策，Agent 自主度高                         │
│    缺点：通信开销大                                          │
│                                                             │
│  算法四：合同网协议 (Contract Net Protocol)                   │
│    更完整的协商流程：                                        │
│      Announcement → Bidding → Award → Execution → Result    │
│    适用：需要对任务分配进行议价和协商的场景                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2.4 冲突检测与解决

多 Agent 同时操作共享资源时可能产生冲突：

```text
冲突类型与解决方案：

1. 资源竞争冲突
   场景：Agent A 和 Agent B 同时修改同一个文件
   检测：文件锁 (flock) / 版本号 (乐观锁)
   解决：
     - 乐观锁：检测到版本冲突时，后提交者收到冲突通知，
       获取最新版本后重做修改
     - 悲观锁：操作前获取锁，操作后释放锁

2. 决策分歧
   场景：两个 Agent 对同一问题给出矛盾的建议
   检测：输出一致性校验
   解决：
     - 引入 Reviewer Agent 做最终裁决
     - 少数服从多数（3 个以上 Agent 投票）
     - 升级到用户决策

3. 目标冲突
   场景：Agent A 要删除的文件，Agent B 正在使用
   检测：依赖关系图分析
   解决：
     - 优先级机制：高优先级 Agent 的操作优先
     - 协调者介入：识别冲突 → 通知双方 → 协商解决
```

#### 2.5 共享状态与共识

```text
共享状态管理方案：

方案 A: 集中式状态存储 (Redis / etcd)
  所有 Agent 读写同一个状态存储
  优点：实现简单，一致性强
  缺点：中心化单点

方案 B: 事件溯源 (Event Sourcing)
  所有状态变更以事件形式记录
  每个 Agent 通过重放事件构建当前状态
  优点：可追溯、可重放、天然解耦
  缺点：事件数量增长，重放成本高

方案 C: 共享黑板 (Blackboard)
  公共的"黑板"区域，Agent 在上面读写信息
  适用于 Agent 间需要共享中间结果的场景
  优点：灵活，支持增量信息交换
  缺点：黑板内容可能冲突
```

### 三、完整系统设计示例

```python
"""
多 Agent 协作系统——通信与任务分配的完整实现

架构: Hub-Spoke + 消息总线混合模式
通信: 结构化 AgentMessage + Redis Pub/Sub
分配: 能力最优匹配 + 竞标混合策略
"""

import asyncio
import json
import random
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable


# ==========================================
# 消息与通信基础设施
# ==========================================

class MessageType(Enum):
    TASK_ASSIGN = "task_assign"
    TASK_RESULT = "task_result"
    TASK_BID = "task_bid"
    QUERY = "query"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    HEARTBEAT = "heartbeat"
    CONFLICT = "conflict"


@dataclass
class AgentMessage:
    message_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    sender_id: str = ""
    receiver_id: str = ""
    msg_type: MessageType = MessageType.QUERY
    task_id: Optional[str] = None
    content: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class MessageBus:
    """消息总线：Agent 间通信的核心基础设施

    简化实现——实际生产中使用 Redis Pub/Sub 或 NATS
    """

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}
        self._message_log: list[AgentMessage] = []

    def subscribe(self, agent_id: str, handler: Callable):
        """Agent 订阅自己的消息通道"""
        if agent_id not in self._subscribers:
            self._subscribers[agent_id] = []
        self._subscribers[agent_id].append(handler)

    async def send(self, message: AgentMessage):
        """发送消息"""
        self._message_log.append(message)

        # 路由到接收者或广播
        if message.receiver_id:
            # 点对点
            handlers = self._subscribers.get(message.receiver_id, [])
        else:
            # 广播
            handlers = []
            for agent_handlers in self._subscribers.values():
                handlers.extend(agent_handlers)

        for handler in handlers:
            await handler(message)


# ==========================================
# 任务系统
# ==========================================

@dataclass
class Task:
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    required_skills: list[str] = field(default_factory=list)
    status: str = "pending"  # pending / assigned / in_progress / completed / failed
    assigned_to: Optional[str] = None
    result: Optional[str] = None
    parent_id: Optional[str] = None
    dependencies: list[str] = field(default_factory=list)


# ==========================================
# Agent 基类
# ==========================================

class BaseAgent(ABC):
    """多 Agent 系统中的 Agent 基类"""

    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        skills: list[str],
        bus: MessageBus,
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.skills = skills
        self.bus = bus
        self.current_tasks: list[str] = []
        self.max_concurrent = 3
        self.inbox: list[AgentMessage] = []

    async def start(self):
        """启动 Agent，订阅消息"""
        await self.bus.subscribe(self.agent_id, self._handle_message)
        print(f"[{self.agent_id}] 已启动 (类型: {self.agent_type})")

    async def _handle_message(self, message: AgentMessage):
        """消息处理入口"""
        self.inbox.append(message)

        if message.msg_type == MessageType.TASK_ASSIGN:
            await self._handle_task_assign(message)
        elif message.msg_type == MessageType.TASK_BID:
            await self._handle_task_bid(message)
        elif message.msg_type == MessageType.QUERY:
            await self._handle_query(message)
        elif message.msg_type == MessageType.TASK_RESULT:
            await self._handle_task_result(message)
        elif message.msg_type == MessageType.BROADCAST:
            await self._handle_broadcast(message)

    @abstractmethod
    async def _handle_task_assign(self, message: AgentMessage):
        """处理任务分配"""
        ...

    @abstractmethod
    async def _handle_task_bid(self, message: AgentMessage):
        """处理竞标请求"""
        ...

    async def _handle_query(self, message: AgentMessage):
        """处理信息查询"""
        pass

    async def _handle_task_result(self, message: AgentMessage):
        """处理任务结果"""
        pass

    async def _handle_broadcast(self, message: AgentMessage):
        """处理广播消息"""
        pass

    async def send_message(
        self, receiver_id: str, msg_type: MessageType,
        content: dict, task_id: Optional[str] = None,
    ):
        """发送消息的便捷方法"""
        await self.bus.send(AgentMessage(
            sender_id=self.agent_id,
            receiver_id=receiver_id,
            msg_type=msg_type,
            task_id=task_id,
            content=content,
        ))

    def can_handle(self, task: Task) -> float:
        """计算自己处理该任务的能力分数 (0-1)"""
        skill_overlap = len(
            set(task.required_skills) & set(self.skills)
        )
        skill_score = skill_overlap / max(len(task.required_skills), 1)
        load_penalty = len(self.current_tasks) / self.max_concurrent
        return skill_score * (1 - load_penalty * 0.3)


# ==========================================
# Orchestrator：任务分配核心
# ==========================================

class Orchestrator(BaseAgent):
    """中心调度者——负责任务分解、分配和协调"""

    def __init__(self, bus: MessageBus):
        super().__init__(
            agent_id="orchestrator",
            agent_type="orchestrator",
            skills=["planning", "coordination", "decomposition"],
            bus=bus,
        )
        self.registry: dict[str, BaseAgent] = {}
        self.tasks: dict[str, Task] = {}
        self._bidding_results: dict[str, list[tuple[str, float]]] = {}

    def register_agent(self, agent: BaseAgent):
        """注册一个工作 Agent"""
        self.registry[agent.agent_id] = agent

    async def decompose_and_assign(self, user_request: str) -> list[Task]:
        """任务分解（简化版——实际生产中使用 LLM 驱动分解）"""

        # 步骤 1: 分解任务（简化示例）
        subtasks = self._decompose(user_request)

        # 步骤 2: 构建依赖图
        for task in subtasks:
            self.tasks[task.task_id] = task

        # 步骤 3: 分配就绪任务（无依赖或依赖已完成）
        ready_tasks = [
            t for t in subtasks
            if not t.dependencies
            or all(
                self.tasks.get(d) and self.tasks[d].status == "completed"
                for d in t.dependencies
            )
        ]

        for task in ready_tasks:
            await self._assign_task(task)

        return subtasks

    def _decompose(self, request: str) -> list[Task]:
        """任务分解（示例：基于关键词的模板匹配）"""
        if "Web" in request and "部署" in request:
            return [
                Task("t1", "需求分析和技术选型", ["analysis", "planning"]),
                Task("t2", "后端 API 开发", ["python", "fastapi", "database"],
                     dependencies=["t1"]),
                Task("t3", "前端页面开发", ["react", "typescript", "css"],
                     dependencies=["t1"]),
                Task("t4", "集成测试", ["testing", "integration"],
                     dependencies=["t2", "t3"]),
                Task("t5", "部署上线", ["devops", "docker", "kubernetes"],
                     dependencies=["t4"]),
            ]
        elif "数据分析" in request:
            return [
                Task("t1", "数据清洗和预处理", ["python", "pandas"]),
                Task("t2", "特征工程", ["python", "sklearn"],
                     dependencies=["t1"]),
                Task("t3", "模型训练", ["python", "ml", "pytorch"],
                     dependencies=["t2"]),
                Task("t4", "结果可视化", ["python", "visualization"],
                     dependencies=["t3"]),
            ]
        else:
            return [Task("t1", request, ["general"])]

    async def _assign_task(self, task: Task):
        """任务分配——使用能力最优匹配 + 竞标混合策略"""

        if len(self.registry) <= 2:
            # Agent 少时直接用最优匹配
            best_agent = self._best_fit(task)
        else:
            # Agent 多时使用竞标策略
            best_agent = await self._auction_task(task)

        if best_agent:
            task.status = "assigned"
            task.assigned_to = best_agent
            print(f"[Orchestrator] 任务 {task.task_id} → {best_agent}")

            await self.send_message(
                receiver_id=best_agent,
                msg_type=MessageType.TASK_ASSIGN,
                content={
                    "task_id": task.task_id,
                    "description": task.description,
                    "required_skills": task.required_skills,
                },
                task_id=task.task_id,
            )
        else:
            print(f"[Orchestrator] 警告：没有 Agent 能处理任务 {task.task_id}")

    def _best_fit(self, task: Task) -> Optional[str]:
        """能力最优匹配"""
        best_agent_id = None
        best_score = 0.0

        for agent_id, agent in self.registry.items():
            if agent_id == self.agent_id:
                continue
            score = agent.can_handle(task)
            if score > best_score:
                best_score = score
                best_agent_id = agent_id

        return best_agent_id if best_score > 0.3 else None

    async def _auction_task(self, task: Task) -> Optional[str]:
        """竞标分配"""
        # 广播竞标请求
        self._bidding_results[task.task_id] = []
        await self.send_message(
            receiver_id="",
            msg_type=MessageType.TASK_BID,
            content={
                "task_id": task.task_id,
                "description": task.description,
                "required_skills": task.required_skills,
            },
            task_id=task.task_id,
        )

        # 等待收集竞标（实际生产中用 asyncio.wait_for 超时控制）
        await asyncio.sleep(0.5)

        bids = self._bidding_results.get(task.task_id, [])
        if not bids:
            return None

        # 选择最高分
        bids.sort(key=lambda x: x[1], reverse=True)
        return bids[0][0]

    async def _handle_task_bid(self, message: AgentMessage):
        """处理竞标"""
        task_id = message.content["task_id"]
        # Agent 返回自己能处理该任务的信心分数
        if task_id in self._bidding_results:
            score = message.content.get("bid_score", 0)
            self._bidding_results[task_id].append(
                (message.sender_id, score)
            )

    async def _handle_task_result(self, message: AgentMessage):
        """处理任务完成结果"""
        task_id = message.task_id
        if task_id and task_id in self.tasks:
            self.tasks[task_id].status = message.content.get(
                "success", False
            ) and "completed" or "failed"
            self.tasks[task_id].result = message.content.get("result", "")

            # 释放依赖此任务的其他任务
            for task in self.tasks.values():
                if (
                    task.status == "pending"
                    and task_id in task.dependencies
                    and all(
                        self.tasks.get(d)
                        and self.tasks[d].status == "completed"
                        for d in task.dependencies
                    )
                ):
                    await self._assign_task(task)

    async def _handle_task_assign(self, message: AgentMessage):
        """Orchestrator 自己不执行任务"""
        pass


# ==========================================
# 工作 Agent
# ==========================================

class WorkerAgent(BaseAgent):
    """执行具体任务的工作 Agent"""

    def __init__(
        self, agent_id: str, agent_type: str,
        skills: list[str], bus: MessageBus,
    ):
        super().__init__(agent_id, agent_type, skills, bus)

    async def _handle_task_assign(self, message: AgentMessage):
        """收到任务分配——执行任务"""
        task_id = message.content["task_id"]
        description = message.content["description"]
        print(f"[{self.agent_id}] 接收任务 {task_id}: {description}")

        self.current_tasks.append(task_id)

        # 模拟执行任务
        await asyncio.sleep(random.uniform(0.5, 2.0))

        # 返回结果
        result = f"[{self.agent_id}] 完成任务 {task_id}"
        self.current_tasks.remove(task_id)

        await self.send_message(
            receiver_id="orchestrator",
            msg_type=MessageType.TASK_RESULT,
            content={
                "task_id": task_id,
                "success": True,
                "result": result,
            },
            task_id=task_id,
        )

    async def _handle_task_bid(self, message: AgentMessage):
        """收到竞标请求——返回竞标分数"""
        task = Task(
            task_id=message.content["task_id"],
            description=message.content["description"],
            required_skills=message.content["required_skills"],
        )
        score = self.can_handle(task)

        if score > 0.3:  # 只有足够的信心才参与竞标
            await self.send_message(
                receiver_id="orchestrator",
                msg_type=MessageType.TASK_BID,
                content={
                    "task_id": task.task_id,
                    "bid_score": score,
                    "agent_skills": self.skills,
                },
                task_id=task.task_id,
            )


# ==========================================
# 完整系统演示
# ==========================================

async def demo_multi_agent_system():
    print("=" * 60)
    print("多 Agent 协作系统演示")
    print("=" * 60)

    # 创建消息总线
    bus = MessageBus()

    # 创建 Orchestrator
    orchestrator = Orchestrator(bus)
    await orchestrator.start()

    # 创建工作 Agent（异构能力）
    workers = [
        WorkerAgent("backend_dev", "executor",
                    ["python", "fastapi", "database", "analysis"], bus),
        WorkerAgent("frontend_dev", "executor",
                    ["react", "typescript", "css"], bus),
        WorkerAgent("devops_eng", "executor",
                    ["devops", "docker", "kubernetes", "testing"], bus),
        WorkerAgent("data_scientist", "executor",
                    ["python", "ml", "pytorch", "pandas", "visualization"], bus),
    ]

    # 注册并启动
    for worker in workers:
        orchestrator.register_agent(worker)
        await worker.start()

    # 用户请求
    print("\n用户请求: '从零搭建一个 Web 应用并部署'\n")

    # 分解并分配任务
    tasks = await orchestrator.decompose_and_assign(
        "从零搭建一个 Web 应用并部署"
    )

    # 等待所有任务完成
    await asyncio.sleep(5)

    # 输出结果
    print("\n" + "=" * 60)
    print("任务执行摘要")
    print("=" * 60)
    for task in tasks:
        status_icon = "✅" if task.status == "completed" else "⏳"
        print(
            f"  {status_icon} {task.task_id}: {task.description}"
            f" → {task.assigned_to or '未分配'}"
            f" [{task.status}]"
        )

    print("\n通信消息数:", len(bus._message_log))
    for msg in bus._message_log[:5]:  # 前5条
        print(
            f"  [{msg.sender_id}] → [{msg.receiver_id}] "
            f"{msg.msg_type.value}: {msg.content.get('task_id', '')}"
        )


if __name__ == "__main__":
    asyncio.run(demo_multi_agent_system())
```

### 四、核心设计原则总结

| 原则               | 说明                                                 |
| ------------------ | ---------------------------------------------------- |
| **明确通信边界**   | 定义哪些信息需要 Agent 间通信，哪些在 Agent 内部处理 |
| **结构化消息**     | 使用统一的 Message Schema，保证可解析性和可追溯性    |
| **最小上下文传递** | 默认传递最小上下文，按需扩展，避免 Token 浪费        |
| **能力可发现**     | 通过 Agent Registry 实现 Agent 能力的自动发现和匹配  |
| **失败可恢复**     | 任务失败时有重试和移交机制，不被单个 Agent 阻塞      |
| **通信可追溯**     | 所有 Agent 间通信可记录、可审计、可回放              |
| **约定优于配置**   | 预定义通信协议和消息格式，减少 Agent 间的理解歧义    |

### 五、知识扩展

- **多 Agent 协作（2.20 节）**：本节侧重通信机制和任务分配的具体实现，2.20 节侧重大概念和模式。
- **A2A 协议与 Agent Card（2.32 节）**：Google A2A 协议是跨框架 Agent 通信的工业标准，Agent Card 是能力注册的核心。
- **SubAgent 机制（2.34 节）**：子 Agent 的上下文传递（promptMode）与本节的通信策略有直接关联。
- **MCP 协议**：工具层的标准化调用协议，与 Agent 间通信协议处于不同层次但相互配合。
- **分布式系统设计**：多 Agent 系统本质上是分布式系统，CAP 理论、一致性协议（Raft/Paxos）等基础概念同样适用。
- **多 Agent RL（强化学习）**：当 Agent 需要通过与环境交互学习协作策略时，多 Agent RL 是重要的技术方向。
- **并发控制**：多 Agent 操作共享资源时的锁机制、乐观并发控制、事务隔离等。
- **Agent 注册与服务发现**：Consul、etcd、Nacos 等服务发现组件可用于 Agent 的注册与健康检查。

### 完整口头回答

设计一个多智能体协作系统，核心要规划好通信机制和任务分配两个方面。

通信机制上，首先要选择架构模式。星型结构最简单——一个 Orchestrator 作为中心调度所有 Agent，适合任务有明确依赖关系的场景；网状结构更灵活但拓扑复杂，适合去中心化协作；混合型通过消息总线兼顾灵活性和可管理性，是工业界推荐的做法。通信内容要结构化，每条消息应包含消息 ID、发送方、接收方、消息类型（任务分配/结果/查询/广播/心跳）、优先级、任务上下文以及期望的回复超时。通信协议的选择取决于部署场景——同集群用 gRPC 或 NATS 获得极低延迟，跨平台用 A2A 协议实现标准化，大量异步消息用 Kafka，轻量广播用 Redis Pub/Sub。上下文传递策略上，默认采用选择性上下文——根据接收方的角色和任务有选择地传递相关背景，在信息完整性和 Token 效率间取得平衡。

任务分配上，首先需要建立 Agent 能力注册中心——每个 Agent 声明自己的技能标签、专精程度、可用工具集和最大并行任务数。分解任务时，可以采用声明式分解（构建 DAG 依赖图）、LLM 驱动分解或模板匹配。分配算法有四种选择：能力最优匹配（找到技能最匹配且负载最低的 Agent）、负载均衡（轮询分配，适合同构 Agent）、竞标拍卖（广播任务请求，各 Agent 根据自身能力出价，Orchestrator 选择最优出价）、合同网协议（更完整的 Announce→Bid→Award→Execute→Result 流程）。还需要设计冲突检测与解决机制——文件操作冲突用锁（乐观锁或悲观锁）、决策分歧引入 Reviewer Agent 或投票机制、目标冲突通过优先级和协调者介入解决。

关键设计原则：明确通信边界（什么需要通信、什么内部处理）、结构化消息（统一 Schema）、最小上下文传递（默认最小、按需扩展）、能力可发现（Agent Registry）、失败可恢复（重试和移交）、通信可追溯（全量日志可审计）。

## 2.40 如何评估一个 AI Agent 的质量？有哪些评估指标、方法和框架？

评估 AI Agent 远比评估传统软件复杂——Agent 的输出是非确定性的、多步推理的、依赖外部工具和环境的。需要一个多维度、分层次的评估体系。

### 一、评估维度体系

#### 1.1 六维评估模型

```text
┌─────────────────────────────────────────────────────────────┐
│                Agent 六维评估模型                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│          ┌──────────┐                                       │
│          │  任务完成 │ ← 最核心：能做对事吗？                │
│          └────┬─────┘                                       │
│               │                                             │
│     ┌─────────┼─────────┐                                   │
│     │         │         │                                   │
│  ┌──▼──┐  ┌──▼──┐  ┌──▼──┐                                 │
│  │效率  │  │质量  │  │鲁棒  │                                │
│  │      │  │      │  │      │                                │
│  │多快？│  │多好？│  │多稳？│                               │
│  └──┬──┘  └──┬──┘  └──┬──┘                                 │
│     │         │         │                                   │
│     └─────────┼─────────┘                                   │
│               │                                             │
│     ┌─────────┼─────────┐                                   │
│     │         │         │                                   │
│  ┌──▼──┐  ┌──▼──┐  ┌──▼───┐                                │
│  │安全  │  │成本  │  │用户   │                               │
│  │      │  │      │  │体验   │                               │
│  │危险？│  │昂贵？│  │好用？ │                               │
│  └─────┘  └─────┘  └──────┘                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 1.2 各维度指标详解

| 维度         | 核心指标              | 定义                            | 测量方式                |
| ------------ | --------------------- | ------------------------------- | ----------------------- |
| **任务完成** | 成功率 (Success Rate) | 任务最终达到目标的比率          | 自动校验 + 人工标注     |
|              | 子任务完成率          | 分解后的子步骤完成比例          | DAG 依赖图状态追踪      |
|              | 首次通过率 (FTR)      | 一次就做对、无需重试的比例      | 无重试完成计数          |
| **效率**     | 平均完成时间          | 从请求到任务完成的耗时          | 端到端计时              |
|              | Token 效率            | 单位任务消耗的 Token 数         | Token 计数器            |
|              | 工具调用次数          | 完成任务的平均工具调用数        | 调用链计数              |
|              | 迭代轮次              | Agent 循环的平均迭代次数        | 循环计数器              |
| **质量**     | 答案正确性            | 输出答案的事实准确度            | 自动校验 / LLM-as-Judge |
|              | 代码质量 (如涉及)     | 可运行性、可维护性、测试覆盖率  | 静态分析 + 测试执行     |
|              | 完整性                | 回答是否覆盖了用户的所有要求    | LLM-as-Judge            |
| **鲁棒性**   | 重试恢复率            | 失败后能成功恢复的比例          | 重试后成功率            |
|              | 输入扰动稳定性        | 对近义改写/拼写错误是否输出一致 | 变体测试                |
|              | 异常处理能力          | 面对异常工具输出时能否优雅处理  | 注入故障测试            |
| **安全**     | 拒答率                | 对危险请求正确拒绝的比例        | 安全测试集              |
|              | 越狱成功率            | 被绕过安全限制的比例（期望低）  | 红队测试                |
|              | PII 泄漏率            | 输出中包含个人隐私信息的比例    | 正则 + NER 检测         |
| **成本**     | 单任务平均成本        | Token 费用 + 工具调用费用       | 账单统计                |
|              | 成本-成功率曲线       | 不同成本预算下的成功率变化      | 预算梯度测试            |
| **用户体验** | 满意度评分            | 用户对回答的满意度 (1-5)        | 显式评分 + 隐式信号     |
|              | 重复提问率            | 用户因不满而重复/追问的比例     | 会话分析                |

### 二、评估方法

#### 2.1 基准测试 (Benchmark)

```text
┌─────────────────────────────────────────────────────────────┐
│                  主流 Agent 评估基准                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  SWE-Bench (软件工程)                                        │
│    ├─ 任务：修复 GitHub Issue，提交 PR                      │
│    ├─ 指标：Resolved Rate（问题解决率）                     │
│    └─ 代表：Devin, SWE-Agent, Claude Code                   │
│                                                             │
│  WebArena (Web 操作)                                         │
│    ├─ 任务：在真实网站完成购物、搜索、协作等操作             │
│    ├─ 指标：Task Success Rate                              │
│    └─ 环境：GitLab, Amazon, Reddit 等真实网站              │
│                                                             │
│  OSWorld (操作系统操作)                                      │
│    ├─ 任务：在真实 OS 环境中完成文件管理、配置等操作         │
│    ├─ 指标：Task Success Rate                              │
│    └─ 环境：Ubuntu VM                                       │
│                                                             │
│  GAIA (通用 AI 助手)                                         │
│    ├─ 任务：推理、多模态、工具使用、编码                     │
│    ├─ 指标：正确率 (3 级难度)                               │
│    └─ 特点：防数据泄露设计，人类基线 92%                    │
│                                                             │
│  τ-Bench (工具使用基准)                                      │
│    ├─ 任务：模拟用户与 Agent 交互，评估工具使用              │
│    ├─ 指标：任务成功率、工具调用准确率                      │
│    └─ 特点：自动化 + 可重复                                 │
│                                                             │
│  BIG-Bench / MMLU (通用能力)                                 │
│    ├─ 覆盖：推理、知识、数学、代码等                         │
│    └─ 缺点：不评估工具使用和多步规划能力                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2.2 LLM-as-Judge

使用更强的模型作为评判者，评估 Agent 的输出质量：

```python
class LLMJudge:
    """LLM-as-Judge：用更强的模型评估 Agent 输出"""

    EVAL_PROMPT = """你是一个 Agent 输出质量评估专家。请根据以下标准评分。

## 评分维度（每项 1-5 分）

1. 正确性 (Correctness)：回答是否符合事实？代码是否可运行？
2. 完整性 (Completeness)：是否覆盖了所有要求？
3. 高效性 (Efficiency)：推理路径是否高效？有无冗余步骤？
4. 工具使用 (Tool Use)：工具选择和调用是否恰当？
5. 鲁棒性 (Robustness)：是否考虑了边界情况和错误处理？

## 用户请求
{user_request}

## Agent 输出
{agent_output}

## Agent 执行轨迹（工具调用链）
{agent_trajectory}

## 输出格式（严格 JSON）
{{
    "correctness": <1-5>,
    "completeness": <1-5>,
    "efficiency": <1-5>,
    "tool_use": <1-5>,
    "robustness": <1-5>,
    "overall": <1-5>,
    "reasoning": "<评分理由>",
    "issues": ["<问题 1>", "<问题 2>"]
}}
"""

    def evaluate(
        self,
        user_request: str,
        agent_output: str,
        agent_trajectory: str,
        judge_llm,
    ) -> dict:
        prompt = self.EVAL_PROMPT.format(
            user_request=user_request,
            agent_output=agent_output,
            agent_trajectory=agent_trajectory,
        )
        result = judge_llm.generate(prompt)
        return json.loads(result)
```

**LLM-as-Judge 的局限性**：
- 裁判模型自身也有偏差（偏好长回答、偏好自己的输出风格）
- 对需要实地验证的判断不可靠（代码可运行性不能只看不跑）
- 裁判间的一致性需要通过多个裁判取均值来提升

#### 2.3 人工评估 (Human Evaluation)

```text
人工评估适用场景：
  ├─ 安全敏感性任务（医疗、法律建议）
  ├─ 主观质量判断（创意写作、对话体验）
  ├─ 新场景的早期验证（无自动评估手段时）
  └─ 基准真值标注（为自动评估提供 Ground Truth）

评估维度：正确性、有用性、安全性、流畅性、满意度

注意事项：
  ├─ 至少 3 位评估者，计算评分者间一致性 (Cohen's Kappa)
  ├─ 盲评：评估者不知道是哪个 Agent 生成的输出
  └─ 标准化的评估指南和校准流程
```

#### 2.4 对抗评估 (Adversarial Evaluation)

主动寻找 Agent 的薄弱点：

```text
对抗评估方法：

1. 红队测试 (Red Teaming)
   组建专门团队，针对性寻找 Agent 的漏洞
   目标：发现安全漏洞、越狱路径、危险行为

2. 变异测试 (Mutation Testing)
   对正常输入做微小变化，检查输出是否稳定
   示例：
     "帮我写一个排序算法"
     "帮我写一个排序算法（用 Python）"
     "help me write a sorting algorithm"
     "帮我写一个排序算发"（故意错字）
   → 期望：核心行为一致

3. 边界测试 (Boundary Testing)
   测试极端输入：
     - 超长输入
     - 空输入
     - 特殊字符/Emoji
     - 多语言混合
     - 矛盾指令

4. 对抗攻击 (Adversarial Attack)
   注入恶意指令、构造误导性上下文
   测试 Agent 是否有足够的防御能力
```

#### 2.5 回归测试 (Regression Testing)

建立 Eval Set 确保迭代不退化：

```text
Agent Eval Set 设计：

1. 覆盖维度
   ├─ 常见任务 (Happy Path)：占 60%
   ├─ 边界情况 (Edge Cases)：占 20%
   ├─ 错误恢复 (Error Recovery)：占 10%
   └─ 安全测试 (Safety Checks)：占 10%

2. 每次迭代对比
   ├─ 成功率变化
   ├─ Token 消耗变化
   ├─ 延迟变化
   └─ 输出风格变化

3. 自动化执行
   CI/CD 集成：每次 PR 自动跑 Eval Set
   设置质量门禁：成功率下降 > 2% 则阻断合并
```

### 三、评估框架

#### 3.1 分层评估架构

```text
┌─────────────────────────────────────────────────────────────┐
│                   Agent 分层评估架构                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Level 1: 组件级评估 (Component-Level)                       │
│    ├─ LLM 推理能力：MMLU, HumanEval, GSM8K                 │
│    ├─ 工具选择准确率：τ-Bench                             │
│    ├─ Embedding 质量：MTEB                                 │
│    └─ 检索质量：Recall@K, MRR                             │
│                                                             │
│  Level 2: 步骤级评估 (Step-Level)                            │
│    ├─ 单步推理正确率：按步骤验证                            │
│    ├─ 工具调用正确率：参数是否准确                          │
│    └─ 中间状态质量：是否在正确的轨道上                      │
│                                                             │
│  Level 3: 任务级评估 (Task-Level)                            │
│    ├─ 端到端成功率                                          │
│    ├─ 首次通过率 (FTR)                                     │
│    └─ 与人协作效率                                          │
│                                                             │
│  Level 4: 系统级评估 (System-Level)                          │
│    ├─ 吞吐量与并发能力                                      │
│    ├─ 长期稳定性 (多天运行)                                  │
│    ├─ 用户留存率 / NPS                                     │
│    └─ 成本效益比                                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 3.2 在线 vs 离线评估

| 维度     | 离线评估 (Offline)            | 在线评估 (Online)            |
| -------- | ----------------------------- | ---------------------------- |
| **时机** | 上线前 / 迭代中               | 生产环境运行中               |
| **数据** | 固定 Eval Set                 | 真实用户请求                 |
| **优点** | 可重复、可对比、快速          | 反映真实效果、发现未知问题   |
| **缺点** | 可能与真实分布不一致          | 评估成本高、有滞后性         |
| **方法** | Benchmark、LLM-as-Judge、人工 | A/B 测试、用户反馈、生产监控 |
| **频率** | 每次 PR / 每日                | 持续进行                     |

**两者互补**：离线评估保证基础质量不退化，在线评估发现真实世界的问题。

### 四、评估实施流程

```text
┌─────────────────────────────────────────────────────────────┐
│               Agent 评估实施流程                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 定义评估目标                                             │
│     ├─ 明确 Agent 的核心使用场景                             │
│     ├─ 确定关键指标 (哪个维度最重要？)                       │
│     └─ 设定目标值 (成功率 > 85% 等)                         │
│                                                             │
│  2. 构建 Eval Set                                           │
│     ├─ 收集典型任务 (Happy Path)                             │
│     ├─ 覆盖边界情况 (Edge Cases)                            │
│     ├─ 包含回归案例 (之前修过的 Bug)                         │
│     └─ 每个案例包含: 用户输入 + 期望输出 + 评估脚本          │
│                                                             │
│  3. 选择评估方法                                             │
│     ├─ 可自动化的 → 脚本 + LLM-as-Judge                     │
│     ├─ 需要准确性验证的 → 执行验证 (代码跑起来)              │
│     └─ 需要主观判断的 → 人工评估                            │
│                                                             │
│  4. 建立基线                                                 │
│     ├─ 记录当前版本的各指标基线值                            │
│     ├─ 设定退化阈值 (成功率下降 > 2% → 阻断)                │
│     └─ 版本间可对比                                         │
│                                                             │
│  5. 持续评估                                                 │
│     ├─ CI 集成：每次 PR 自动跑 Eval                          │
│     ├─ 定期评估：每周全量跑 + 生成报告                       │
│     └─ 生产监控：在线指标实时仪表盘                          │
│                                                             │
│  6. 反馈优化                                                 │
│     ├─ 分析失败案例 → 改进 Prompt / 工具设计                 │
│     ├─ 更新 Eval Set → 加入新发现的边界情况                  │
│     └─ 调整目标值 → 根据实际情况迭代                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 五、知识扩展

- **LLM 评估基础**：理解 Perplexity、ROUGE、BLEU 等基础指标，以及 LLM-as-Judge 的原理和局限。
- **Prompt 质量评估（12.x 节）**：Prompt 评估是 Agent 评估的重要组成部分，评估方法有共通之处。
- **聚类评估指标（13.5 节）**：无监督评估的思想可借鉴到 Agent 的行为聚类分析。
- **A/B 测试**：在线评估的核心方法——分流实验、统计显著性检验、效应量分析。
- **RLHF 中的评估**：奖励模型本质上就是一种自动评估器，其训练目标与 Agent 评估的 LLM-as-Judge 高度相关。
- **Agent 可解释性**：评估不仅是看结果，还需要理解 Agent **为什么**做出某个决策，可解释性工具（注意力可视化、推理链分析）辅助评估。
- **对抗性红队**：安全评估的专门技术，需要建立系统化的红队测试流程和威胁模型。
- **持续评估系统**：建立 CI/CD + Eval 的自动化评估流水线，包括 Eval Set 的版本管理和退化检测。

### 完整口头回答

评估一个 AI Agent 的质量，需要建立六维评估模型。任务完成维度最核心，关注成功率、子任务完成率和首次通过率。效率维度关注完成时间、Token 消耗和工具调用次数。质量维度关注答案正确性、代码质量和完整性。鲁棒性维度关注重试恢复率、输入扰动稳定性和异常处理能力。安全维度关注拒答率、越狱成功率和 PII 泄漏率。成本维度关注单任务平均成本和成本-成功率曲线。用户体验维度关注满意度评分和重复提问率。

评估方法上，首先是基准测试——SWE-Bench 评估软件工程能力、WebArena 评估 Web 操作能力、GAIA 评估通用 AI 助手能力、τ-Bench 评估工具使用能力。其次是 LLM-as-Judge——用更强的模型对输出进行多维度打分，但需要注意裁判模型自身的偏差。人工评估在安全敏感场景和主观判断中不可或缺，需要多位评估者。对抗评估通过红队测试、变异测试、边界测试主动寻找 Agent 的薄弱点。回归测试通过建立 Eval Set，在每次迭代中自动对比各指标变化，防止质量退化。

评估框架上，建议建立四层评估架构：组件级评估（LLM 推理能力、工具选择准确率）、步骤级评估（单步推理正确率）、任务级评估（端到端成功率）、系统级评估（吞吐量、长期稳定性）。同时区分离线评估和在线评估——离线评估用固定 Eval Set 保证基础质量不退化，在线评估通过 A/B 测试和用户反馈发现真实问题。最终通过 CI/CD 集成实现自动化：每次 PR 自动跑 Eval Set，成功率下降超过阈值则阻断合并，持续迭代 Eval Set 覆盖新的边界情况。

## 2.41 在多轮对话中，如何让 Agent 保持对话的一致性和连贯性？会遇到哪些挑战，分别有哪些应对策略？

多轮对话是 Agent 最常见的工作模式。随着对话轮次增加，Agent 面临上下文漂移 (Context Drift)、意图遗忘、信息矛盾等问题，保持一致性和连贯性成为关键挑战。

### 一、核心挑战

#### 1.1 上下文漂移 (Context Drift)

这是多轮 Agent 最核心的问题——随着对话增长，模型的输出逐渐偏离初始目标和约束。

```text
┌─────────────────────────────────────────────────────────────┐
│                    上下文漂移示意                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   第 1 轮：用户："帮我用 Python 写一个高并发 Web API"       │
│            Agent：分析需求，确定用 FastAPI + asyncio        │
│                                                             │
│   第 5 轮：Agent 在讨论数据库优化                            │
│            ↑ 仍在主线                                        │
│                                                             │
│   第 15 轮：Agent 开始讨论前端 React 组件                    │
│            ↑ 已经偏离"高并发"的核心约束                     │
│                                                             │
│   第 30 轮：Agent 完全忘记了初始的性能要求                    │
│            ↑ 上下文漂移到完全不同的方向                      │
│                                                             │
│  关键发现 (2025 研究)：漂移不是无界衰减，而是趋于            │
│  噪声限制的均衡态。目标不是"完全阻止漂移"，而是             │
│  "将均衡态控制在可接受水平"。                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 1.2 五大挑战类型

| 挑战类型                                | 表现                                       | 根因                                 | 严重度 |
| --------------------------------------- | ------------------------------------------ | ------------------------------------ | ------ |
| **意图侵蚀 (Intent Erosion)**           | 逐渐遗忘用户的原始指令和约束               | 对话过长，早期信息被"挤出"注意力窗口 | 高     |
| **跨轮矛盾 (Cross-Turn Contradiction)** | 第 10 轮和第 20 轮给出矛盾的建议           | 缺乏全局一致性校验                   | 高     |
| **信息断层 (Information Gap)**          | 引用前文未提及的信息，或遗忘已讨论过的内容 | 上下文压缩丢失关键信息               | 中     |
| **风格漂移 (Style Drift)**              | 回复风格从技术专家变成闲聊模式             | 对话节奏变化，缺乏风格锚定           | 低     |
| **目标置换 (Goal Displacement)**        | 把手段当目的，忘了最终目标                 | 沉浸在某个子任务的细节中             | 中     |

#### 1.3 Lost in the Middle 效应

```text
对话位置对 Agent 注意力的影响：

  System Prompt    [████████████████]  高注意力 ✅
  第 1-2 轮        [████████████████]  高注意力 ✅
  第 3-10 轮       [████░░░░░░░░░░░░]  中注意力 ⚠️
  第 11-25 轮      [██░░░░░░░░░░░░░░]  低注意力 ❌  ← 关键信息最容易被忽略
  第 26-30 轮      [████████████████]  高注意力 ✅

→ "中间信息"最容易被忽略，而这里往往存放着关键决策和上下文
→ 需要对抗这个效应来保持一致性
```

### 二、应对策略

#### 2.1 策略一：结构化状态管理

不依赖 Agent "记住"一切，而是显式维护关键状态：

```python
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConversationState:
    """对话状态——显式维护，不依赖 Agent 隐式记忆"""

    # 不可变核心（每个对话轮次都注入）
    user_goal: str = ""                    # 用户的核心目标
    constraints: list[str] = field(default_factory=list)  # 约束条件
    preferences: dict = field(default_factory=dict)       # 用户偏好
    persona: str = ""                      # Agent 角色定义

    # 可变状态（随对话更新）
    current_phase: str = ""                # 当前阶段
    completed_milestones: list[str] = field(default_factory=list)
    pending_tasks: list[str] = field(default_factory=list)
    key_decisions: list[dict] = field(default_factory=list)
    # 格式: [{"decision": "用 Redis", "reason": "需要缓存高频查询",
    #         "turn": 5}]

    # 一致性守护
    contradictions: list[dict] = field(default_factory=list)
    # 检测到的矛盾记录

    def to_consistency_prompt(self) -> str:
        """生成注入每轮的"一致性守护"提示"""
        parts = [
            "## 对话状态（请保持一致）",
            f"核心目标: {self.user_goal}",
        ]
        if self.constraints:
            parts.append(f"约束条件: {', '.join(self.constraints)}")
        if self.key_decisions:
            parts.append("已做出的关键决策:")
            for d in self.key_decisions[-5:]:  # 最近 5 条
                parts.append(
                    f"  - [第{d['turn']}轮] {d['decision']}: {d['reason']}"
                )
        if self.pending_tasks:
            parts.append(f"待完成: {', '.join(self.pending_tasks)}")
        if self.contradictions:
            parts.append("⚠️ 注意避免以下矛盾:")
            for c in self.contradictions[-3:]:
                parts.append(f"  - {c['description']}")

        # 控制在 500 字符以内，避免膨胀
        text = "\n".join(parts)
        if len(text) > 500:
            text = text[:497] + "..."
        return text
```

#### 2.2 策略二：目标锚定 (Goal Anchoring)

将核心目标作为每轮的"锚"，持续注入上下文：

```text
┌─────────────────────────────────────────────────────────────┐
│                    目标锚定机制                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  每轮 Agent 推理前，注入：                                   │
│                                                             │
│  ┌─────────────────────────────────────────────────┐       │
│  │ [目标锚]                                          │       │
│  │                                                    │       │
│  │ 用户的核心目标是：使用 Python 构建高并发 Web API    │       │
│  │ 关键约束：延迟 < 10ms, 支持 10000 QPS             │       │
│  │ 当前进度：数据库优化阶段                           │       │
│  │                                                    │       │
│  │ 请确保你的回复与上述目标一致。                      │       │
│  │ 如果需要偏离目标，请先向用户确认。                  │       │
│  └─────────────────────────────────────────────────┘       │
│                                                             │
│  策略：定时提醒 (Targeted Reminders)                         │
│    - 每 5 轮自动注入一次目标锚                              │
│    - 检测到话题大幅偏离时主动提醒                          │
│    - 用户确认偏离后才允许改变方向                          │
│                                                             │
│  研究支持：简单目标提醒可可靠地减少上下文漂移               │
│           (Dongre et al., Adobe Research 2025)               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2.3 策略三：熵值监控与主动干预

借鉴 ERGO (NeurIPS 2025) 框架，监控预测熵值来检测一致性风险：

```text
┌─────────────────────────────────────────────────────────────┐
│               熵值监控与干预流程                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  正常运行 (熵值低)                                          │
│    ↓                                                        │
│  检测到熵值飙升 (信号 Agent 变得不确定/混乱)                │
│    ↓                                                        │
│  触发干预:                                                  │
│    ├─ Level 1: 注入目标锚定提示 ("请回顾你的核心目标")     │
│    ├─ Level 2: 压缩并重组上下文 (去掉冗余，突出关键)       │
│    └─ Level 3: 上下文重置 (生成摘要，重新开始)              │
│    ↓                                                        │
│  熵值恢复正常 → 继续对话                                    │
│                                                             │
│  效果: ERGO 框架实现 56.6% 的多轮性能提升                    │
│        35.3% 的性能波动降低                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2.4 策略四：概念级状态管理 (Concept-Level State)

借鉴 CORE 框架 (Dec 2025) 的思想——从 "Token-First" 走向 "Concept-First"：

```text
传统方式 (Token-First):
  每轮把整个对话历史 (原始 Token) 塞进上下文
  问题: Token 膨胀，关键信息被稀释

概念级方式 (Concept-First):
  维护一个紧凑的"概念状态" (Concept State):
    ├─ 任务目标 (Goal)
    ├─ 约束条件 (Constraints)
    ├─ 当前进展 (Progress)
    ├─ 已做决策 (Decisions)
    └─ 开放问题 (Open Questions)

  每轮只注入概念状态 (~200 tokens)
  而非整个对话历史 (~10,000 tokens)

  优势:
    - 减少 42% 的累计 Prompt Token
    - 关键信息始终在注意力窗口内
    - 不会因对话增长而稀释核心信息
```

#### 2.5 策略五：一致性校验层

在每次输出前进行一致性检查：

```python
class ConsistencyChecker:
    """一致性校验——在输出前检查是否与历史决策矛盾"""

    def __init__(self):
        self.decision_log: list[dict] = []  # 历史决策记录

    def log_decision(self, turn: int, decision: str, reason: str):
        self.decision_log.append({
            "turn": turn, "decision": decision, "reason": reason
        })

    def check_consistency(self, proposed_output: str) -> dict:
        """
        检查当前输出是否与历史决策一致

        Returns:
            {"consistent": True/False, "conflicts": [...]}
        """
        conflicts = []

        for past in self.decision_log:
            # 简化的矛盾检测——实际使用 LLM 或语义匹配
            # 检查是否出现了与历史决策相矛盾的建议
            if self._detect_contradiction(
                past["decision"], proposed_output
            ):
                conflicts.append({
                    "past_decision": past,
                    "conflict_in_output": proposed_output[:200],
                })

        return {
            "consistent": len(conflicts) == 0,
            "conflicts": conflicts,
        }

    def _detect_contradiction(
        self, past_decision: str, current_output: str
    ) -> bool:
        """检测矛盾的核心逻辑

        实际生产使用:
        1. LLM 判断: "以下两段话是否矛盾?"
        2. 语义相似度: 用 NLI 模型判断 entailment/contradiction
        3. 规则匹配: 预定义矛盾模式
        """
        # 简化示例：关键词匹配
        contradiction_pairs = [
            ("用 Redis", "用 Memcached"),
            ("同步", "异步"),
            ("MySQL", "PostgreSQL"),
        ]
        for a, b in contradiction_pairs:
            if a in past_decision and b in current_output:
                return True
            if b in past_decision and a in current_output:
                return True
        return False

    def get_intervention_prompt(self, conflicts: list) -> str:
        """生成一致性干预提示"""
        if not conflicts:
            return ""

        conflict_texts = []
        for c in conflicts:
            conflict_texts.append(
                f"  - 之前决定: [{c['past_decision']['turn']}轮] "
                f"{c['past_decision']['decision']}\n"
                f"    当前输出可能矛盾"
            )

        return (
            "⚠️ 检测到与你之前的决策可能矛盾：\n"
            + "\n".join(conflict_texts)
            + "\n请确认是否要改变之前的决策，或修正当前输出。"
        )
```

#### 2.6 策略六：周期性上下文蒸馏

```text
┌─────────────────────────────────────────────────────────────┐
│              周期性上下文蒸馏                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  触发条件:                                                  │
│    ├─ 每 N 轮 (如 N=10)                                     │
│    ├─ Token 使用率 > 阈值                                   │
│    └─ 用户明确提出新话题                                     │
│                                                             │
│  蒸馏流程:                                                  │
│    1. 收集当前对话的核心要素                                 │
│    2. 生成结构化摘要（目标、约束、决策、进展）               │
│    3. 将摘要注入下一轮上下文                                 │
│    4. 清除原始对话历史中已被摘要覆盖的部分                   │
│                                                             │
│  关键原则:                                                  │
│    - 蒸馏不是遗忘，是将离散信息浓缩为结构化知识               │
│    - 保留"为什么" (决策理由) 而不只是"是什么"               │
│    - 增量更新: 在已有摘要上追加，而非每次重建                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 三、策略对比与场景适配

| 策略           | 复杂度 | 效果 | 延迟影响 | 适用场景                 |
| -------------- | ------ | ---- | -------- | ------------------------ |
| 结构化状态管理 | 中     | 高   | 低       | 所有场景（推荐基础策略） |
| 目标锚定       | 低     | 中高 | 极低     | 目标明确的长对话         |
| 熵值监控       | 高     | 高   | 低       | 需要高一致性的关键任务   |
| 概念级状态     | 高     | 高   | 低       | 超长对话 (50+ 轮)        |
| 一致性校验     | 中     | 高   | 中       | 决策密集型任务           |
| 周期性蒸馏     | 中     | 中   | 中       | 对话持续增长时           |

**推荐组合**：结构化状态管理 + 目标锚定 作为基础层，在对话超过 20 轮时启用周期性蒸馏，在决策密集型任务中加一致性校验。

### 四、知识扩展

- **长短期记忆机制（3.1 节）**：本节的一致性保障依赖记忆系统的质量，理解记忆分类和持久化策略是基础。
- **上下文裁剪与压缩（2.36 节）**：周期性蒸馏的核心技术——如何生成高质量的结构化摘要替代原始对话。
- **Agent 评估（2.40 节）**：一致性是 Agent 质量评估的重要维度，需要专门的评估方法和指标。
- **Lost in the Middle**：这是上下文漂移的重要机制性原因——中间位置的对话信息容易被模型忽略，对抗这个效应需要将关键信息始终放在注意力窗口的高关注区间。
- **LLM 的注意力机制**：理解 Transformer 的注意力衰减曲线有助于设计更有效的上下文布局策略。
- **多 Agent 协作中的一致性**：多 Agent 场景下的一致性问题更为复杂——不仅每个 Agent 内部要一致，Agent 之间也要保持一致。
- **对话系统 (Dialogue System)**：传统的任务型对话系统中有对话状态追踪 (DST) 和对话策略 (DP) 的成熟方法论，可借鉴到 Agent 设计中。

### 完整口头回答

在多轮对话中让 Agent 保持一致性和连贯性，面临五大核心挑战。第一是意图侵蚀——对话长了之后 Agent 逐渐遗忘用户的原始指令和约束。第二是跨轮矛盾——不同轮次给出相互矛盾的建议。第三是信息断层——引用未讨论过的信息或遗忘已讨论的内容。第四是风格漂移——回复风格从专业变得随意。第五是目标置换——沉浸在子任务中忘了最终目标。这些挑战的根源在于 Lost in the Middle 效应——Transformer 对中间位置的对话信息注意力最低，而那里往往存放着关键决策。

应对策略有六个。第一，结构化状态管理——显式维护一个"对话状态"对象（核心目标、约束、关键决策、待完成事项），每轮将其注入上下文作为"一致性守护"提示。第二，目标锚定——每隔 N 轮注入一次目标提醒，检测到话题偏离时主动提醒用户确认。研究证明，简单的目标提醒可以可靠地减少上下文漂移。第三，熵值监控——借鉴 ERGO 框架，监控模型的预测熵值，当熵值飙升时说明模型变得不确定，立即触发干预（注入锚定提示 / 重组上下文 / 重置上下文）。第四，概念级状态管理——从 Token-First 走向 Concept-First，维护一个约 200 Token 的紧凑概念状态而非每次塞入完整对话历史，可减少约 42% 的 Prompt Token。第五，一致性校验层——在每次输出前检查是否与历史决策矛盾，如果检测到矛盾则提醒 Agent 修正。第六，周期性上下文蒸馏——每 10 轮或 Token 使用率超过阈值时，将对话核心要素蒸馏为结构化摘要，增量更新而非每次重建。

关键洞察是：上下文漂移不是无界衰减，而是趋于噪声限制的均衡态。因此目标不是"完全阻止漂移"，而是"将均衡态控制在可接受水平"。推荐组合策略：结构化状态管理 + 目标锚定作为基础，超过 20 轮时启用周期性蒸馏，决策密集型任务加一致性校验层。

## 2.42 AI Agent 在量化金融行业中有哪些典型的应用场景与落地路径？请从投研流程自动化、多源数据融合分析、策略生成与迭代、风险监控与预警等维度系统阐述，并分析 Agent 落地量化领域面临的核心挑战（如数据时效性、模型幻觉、合规风控要求等），以及 Agent 对传统量化工作模式的变革意义。

这个问题考察的是将 Agent 技术映射到垂直行业的能力。面试官想听的不是"Agent 能帮量化干活"这种笼统回答，而是你能否把量化投研的具体工作流拆解清楚，然后指出 Agent 在每个环节的切入点、技术方案和工程边界。

先给一句话结论：Agent 在量化行业的核心价值不是替代量化研究员，而是把研究员从高重复性、多源异构的信息处理中解放出来，让他们聚焦在策略逻辑设计和市场直觉判断上。Agent 充当的是一个"永不休息的研究助手 + 自动化执行引擎"的角色。

### 一、量化行业的业务特征：为什么 Agent 天然适配

量化投研的工作流有一条清晰的 Pipeline，而这条 Pipeline 恰好与 Agent 的核心能力高度匹配：

| 量化工作环节       | 工作特征                             | Agent 能力匹配                                                          |
| ------------------ | ------------------------------------ | ----------------------------------------------------------------------- |
| 数据获取与清洗     | 多源异构、格式混乱、需要持续爬取     | 工具调用 (Tool Calling)：Agent 调度爬虫、数据库查询、API 调用等工具     |
| 因子挖掘与验证     | 需要不断尝试大量候选因子、做统计检验 | 规划-执行-反思循环：Agent 生成候选因子 → 执行回测 → 读取结果 → 修正方向 |
| 策略构建与回测     | 逻辑复杂、参数众多、需要迭代调整     | 多步推理 (ReAct / Plan-and-Execute)：Agent 分解策略逻辑，逐步构建和验证 |
| 风险监控与归因     | 需要实时响应、多维度分析             | 自主监控 + 异常检测：Agent 持续监控指标，触发告警时自动归因分析         |
| 研报撰写与知识管理 | 信息密度高、格式规范、需要引用来源   | RAG + 结构化生成：Agent 检索历史研报、市场数据，自动生成结构化报告      |

量化行业的信息处理链路本质上是：**数据 → 因子 → 信号 → 策略 → 执行 → 监控**。这恰好是一个多步骤、强依赖、需反馈的决策链条——正是 Agent 擅长处理的场景。

### 二、四大核心应用场景

#### 1. 投研流程自动化

传统量化投研中，研究员约 60%~70% 的时间花在非核心工作上：数据清洗对齐、报告格式调整、会议纪要整理、文献检索等。Agent 可以自动化这些环节：

**典型场景**：

- **研报自动生成**：Agent 接收"生成一份关于新能源汽车产业链的最新研报"指令后，自动：(1) 检索最近的行业政策、市场数据和竞品动态（RAG 检索）；(2) 调用数据工具获取相关标的估值、财报数据；(3) 整合多源信息，按研报模板生成结构化报告；(4) 自动引用数据来源，标注时间戳。

- **信息聚合摘要**：设定定时任务，Agent 每日开盘前自动抓取隔夜外盘行情、重大新闻、持仓标的相关公告，生成一份 500 字的简报。

- **投研知识库维护**：Agent 持续将研报、会议纪要、策略复盘记录向量化存储，在新任务时自动检索相关历史信息。

**工程实现要点**：

```python
# 投研 Agent 的核心编排逻辑（基于 LangGraph 风格的伪代码）

class QuantResearchAgent:
    """量化投研助手 Agent"""
    
    def __init__(self):
        self.tools = {
            "search_news": NewsSearchTool(),       # 新闻检索
            "query_financials": FinancialDBTool(), # 财务数据查询
            "get_market_data": MarketDataTool(),   # 行情数据
            "run_backtest": BacktestTool(),        # 回测引擎
            "vector_search": RAGRetrievalTool(),   # 研报知识库检索
        }
    
    def execute_task(self, task: str) -> str:
        # Agent 决策循环：分析任务 → 调用工具 → 整合结果
        plan = self.plan_step(task)                # 1. 先做任务分解
        results = []
        for step in plan:
            tool_result = self.call_tool(step)     # 2. 逐步调用工具
            results.append(tool_result)
            plan = self.replan_if_needed(results)  # 3. 根据反馈调整后续步骤
        return self.synthesize_report(results)     # 4. 整合生成最终输出
```

#### 2. 多源数据融合分析

量化行业的数据源极其分散且异构：

```text
┌─────────────────────────────────────────────────────────────┐
│                   多源异构数据层                               │
├───────────┬───────────┬────────────┬───────────┬────────────┤
│  行情数据  │  财务数据  │  另类数据   │  舆情数据  │  宏观数据   │
│  (tick/   │  (季报/   │  (卫星图/   │  (新闻/   │  (GDP/    │
│   K线)    │   年报)   │   供应链)   │  社交媒体) │  CPI/PMI) │
└─────┬─────┴─────┬─────┴──────┬─────┴─────┬─────┴──────┬──────┘
      │           │            │           │            │
      ▼           ▼            ▼           ▼            ▼
┌─────────────────────────────────────────────────────────────┐
│               Agent 数据融合层（统一语义空间）                  │
│  · 时间对齐 (不同频率数据映射到统一时间轴)                      │
│  · 实体关联 (公司→股票→行业→上下游)                            │
│  · 缺失值处理 (节假日对齐、财报滞后补偿)                        │
│  · 异常检测 (数据质量校验、跨源交叉验证)                        │
└─────────────────────────────────────────────────────────────┘
```

Agent 的优势在于：它可以通过 Function Calling 动态选择数据源，通过多步推理判断数据质量，而不是执行一个固定的 ETL 脚本。例如：

- **卫星图像 + 供应链数据 + 行情**：Agent 发现某芯片公司 Fab 厂的卡车流量（卫星图像另类数据）骤降 → 交叉验证供应链订单数据和近期股价 → 生成预警报告。
- **新闻情感 + 技术指标**：Agent 检测到某标的突发利空新闻 → 自动拉取该标的当前技术指标和持仓敞口 → 综合判断是否需要触发风控。

#### 3. 策略生成与迭代

这是 Agent 在量化领域最有想象力的应用方向。传统量化策略开发需要研究员手动设计因子、编写回测代码、分析回测结果、反复调参——整个过程高度依赖个人经验且试错成本高。

Agent 可以以"策略研发助手"的身份参与这一流程：

```text
研究员自然语言描述策略思路
          │
          ▼
┌──────────────────────────────────────┐
│        Agent 策略研发循环             │
│                                      │
│  1. 理解策略逻辑 → 生成因子表达式     │
│           │                          │
│           ▼                          │
│  2. 调用回测引擎执行回测               │
│           │                          │
│           ▼                          │
│  3. 读取回测报告 → 分析问题            │
│     (过度拟合? 容量不足? 信号衰减?)    │
│           │                          │
│           ▼                          │
│  4. 提出改进方向 → 生成新版本因子       │
│           │                          │
│           ▼                          │
│  5. 循环 2~4 直到满足收敛条件          │
│                                      │
│  输出: 策略代码 + 回测报告 + 风险分析   │
└──────────────────────────────────────┘
```

**具体的 Agent-研究员交互示例**：

研究员说："我想测试一个基于成交量异动 + 北向资金流向的短线策略，A 股市场，日频调仓。"

Agent 的处理链路：
1. **解析意图**：识别出"成交量异动"、"北向资金"、"A 股"、"日频"四个关键约束。
2. **因子构建**：从因子库中检索"成交量异动"相关的标准因子（如量比、相对成交量），结合"北向资金净流入率"，生成初始因子表达式。
3. **回测执行**：调用回测引擎，自动设置日频调仓、A 股池、滑点和手续费模型。
4. **结果分析**：读取回测报告的夏普比率、最大回撤、换手率、IC 分析等指标。如果换手率过高，Agent 自动建议加入交易成本惩罚项；如果 IC 衰减快，建议缩短调仓周期测试。
5. **迭代优化**：根据分析结果自动修改因子参数或组合方式，重新回测。

**关键限制**：需要明确，Agent 在这里的角色是"加速器"而非"替代者"。策略的核心逻辑创意仍然来自研究员，Agent 负责的是机械化的实验管理和初步分析。

#### 4. 风险监控与预警

量化交易对实时性和准确性的要求极高。Agent 在风险监控方面有两个层面的价值：

**第一层：被动监控 + 主动归因**

Agent 持续监控以下维度的指标，当触发异常时自动执行归因分析：

```text
监控指标层：
  ├── 策略层：PnL 偏离预期范围、回撤超限、夏普比率骤降
  ├── 执行层：滑点异常、未成交订单堆积、延迟升高
  ├── 市场层：波动率突增、相关性结构突变、流动性枯竭
  └── 合规层：持仓集中度超限、杠杆率超标、单票上限突破

Agent 自动归因流程：
  异常触发 → Agent 拉取多维度数据 → 逐层排除 → 生成归因报告 + 处置建议
```

例如，策略 PnL 出现 3 倍标准差的异常回撤时：
- Agent 自动拉取该时间段的所有交易记录、市场行情、持仓变化
- 逐项排查：是 Alpha 端失效（因子 IC 衰减）还是执行端问题（滑点成本陡增）？
- 如果是因子 IC 衰减 → 进一步检查是该因子的哪个子维度出现反转
- 生成归因报告并推送至风控群，附带建议（如：建议暂时降低该因子权重至 50%，观察 3 个交易日）

**第二层：主动风险感知**

Agent 不只被动等异常触发，还可以主动从非结构化信息中嗅探风险：

- 监控政策文件（如央行报告、监管通知）的措辞变化，预判政策转向
- 追踪产业链上下游公司的财报电话会（Earnings Call）中的"危险词汇"（如需求疲软、库存积压、客户流失）
- 分析社交媒体讨论热度和情感突变，捕捉潜在的流动性危机或恐慌踩踏

### 三、Agent 驱动的量化投研架构

将以上四大场景整合，可以构建一个完整的 Agent 驱动的量化投研平台：

```text
┌──────────────────────────────────────────────────────────────────┐
│                    用户交互层                                     │
│  自然语言指令 · 定时任务 · Web Dashboard · 消息推送 (企微/钉钉)    │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                   Agent 编排层 (核心调度)                         │
│                                                                  │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│   │ 投研Agent │  │ 因子Agent │  │ 风控Agent │  │ 知识管理Agent │  │
│   │ (研报/    │  │ (因子挖掘 │  │ (监控/    │  │ (RAG/研报    │  │
│   │  简报)   │  │  /回测)   │  │  归因)    │  │  检索/摘要)  │  │
│   └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
│        │             │             │               │           │
│        └─────────────┴──────┬──────┴───────────────┘           │
│                             │                                   │
│               ┌─────────────┴─────────────┐                    │
│               │    协调 Agent (Router)     │                    │
│               │  · 意图识别 · 任务分发     │                    │
│               │  · 全局状态管理 · 冲突消解 │                    │
│               └─────────────────────────────┘                   │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                     工具层 (能力原子)                             │
│                                                                  │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────────┐ │
│  │行情数据 │ │财务数据 │ │回测引擎 │ │风控引擎 │ │  RAG 检索引擎 │ │
│  │(实时/  │ │(季报/  │ │(因子/  │ │(VaR/   │ │ (向量库+全文  │ │
│  │ 历史)  │ │ 年报)  │ │ 组合)  │ │ 压力测试)│ │   检索)      │ │
│  └────────┘ └────────┘ └────────┘ └────────┘ └──────────────┘ │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────────┐ │
│  │新闻舆情 │ │另类数据 │ │公告解析 │ │实时推送 │ │  合规校验     │ │
│  │(NLP)   │ │(卫星/  │ │(PDF/   │ │(消息/   │ │  (持仓集中度  │ │
│  │        │ │ 供应链)│ │ 财报)  │ │ 邮件)   │ │   杠杆率)    │ │
│  └────────┘ └────────┘ └────────┘ └────────┘ └──────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                   记忆与知识层                                     │
│  · 短期记忆：当前会话上下文、任务状态、中间结果                      │
│  · 长期记忆：历史策略回测记录、因子表现时序、研报向量库、市场事件日志 │
│  · 工作记忆：因子池、策略版本、白名单标的、黑名单规则                 │
└──────────────────────────────────────────────────────────────────┘
```

### 四、Agent 落地量化领域的核心挑战

#### 1. 数据时效性与低延迟要求

量化交易对时效性的要求是其他行业无法比拟的：

| 场景           | 典型延迟要求 | Agent 能否满足                                                 |
| -------------- | ------------ | -------------------------------------------------------------- |
| 高频交易 (HFT) | < 10μs       | **不适用**——Agent 的 LLM 推理延迟在秒级，完全不是一个量级      |
| 日内中频       | < 100ms      | **勉强**——需要用流式输出 + 预计算缓存，且 LLM 不应在关键路径上 |
| 日频/周频策略  | 分钟级       | **适用**——Agent 的推理延迟不构成瓶颈                           |
| 投研分析       | 非实时       | **最佳场景**——Agent 的核心价值在这里                           |

**工程对策**：
- 把 LLM 决策放在离线/准实时链路，不在交易执行的热路径上
- 高频信号由传统规则引擎处理，Agent 负责策略参数调整和异常归因（"做策略的医生，不做策略的神经"）
- 建立分级响应机制：L0（规则引擎自动处置，<1ms）→ L1（Agent 辅助决策，秒级）→ L2（人工确认，分钟级）

#### 2. 模型幻觉与策略可靠性

这是量化领域对 LLM 最大的顾虑。一个幻觉可能导致错误的因子构建、错误的回测结论、甚至错误的交易决策。

**具体风险场景**：
- 幻觉性因子：Agent "发明"了一个不存在的财务指标（如认为某公司有某项披露但实际上没有）
- 数据混淆：将不同时间段的行情数据错误关联，导致回测结果虚高
- 逻辑跳跃：在归因分析中，Agent 因为"读过类似案例"而跳过了关键的验证步骤

**防御措施**：

```text
┌─────────────────────────────────────────────┐
│           Agent 可靠性保障体系                │
│                                             │
│  输入层  ── 数据溯源校验 (每条数据带时间戳    │
│            + 来源标注，Agent 输出必须引用)    │
│                                             │
│  推理层  ── 关键结论要求交叉验证              │
│           (来自 2 个以上独立数据源的支撑)     │
│                                             │
│  输���层  ── 数值型输出强制 Schema 校验        │
│           (策略参数必须在预设范围内，          │
│            收益预测必须带置信区间)            │
│                                             │
│  执行层  ── 所有交易操作需经合规规则引擎       │
│           二次校验 + 人工确认 (超额操作)      │
│                                             │
│  审计层  ── 全链路日志不可篡改，Agent 的      │
│           每一步决策都有完整轨迹可回溯         │
└─────────────────────────────────────────────┘
```

#### 3. 合规风控的硬约束

量化行业受严格监管。Agent 的自主决策特性与金融合规的"可控、可解释、可追溯"要求之间存在根本张力：

- **可解释性**：监管机构要求策略逻辑可解释。Agent 基于 LLM 的"黑箱推理"天然难以满足。对策：在 Agent 输出策略变更时，强制附带"变更理由 + 支持证据"，形成可审计的决策记录。
- **权限边界**：Agent 绝不应拥有直接下单权限。正确的权限分级是：Agent 只能做分析 → 建议 → 生成指令草稿，最终执行必须经过交易员或风控系统的确认。
- **留痕与回溯**：所有 Agent 决策的完整上下文（输入、推理过程、工具调用链、输出）必须持久化，支持事后回溯审计。

#### 4. 策略知识产权保护的困境

Agent 参与策略开发带来一个微妙的问题：如果 Agent 基于"见过"的所有历史策略数据来生成新策略建议，那么这个新策略的知识产权归谁？它是否在不经意间"借鉴"了不应访问的外部策略逻辑？

**对策**：为 Agent 的知识检索设置严格的权限边界——Agent 只能访问该研究员/团队有权限的数据和策略库，RAG 检索必须在鉴权层过滤，确保不会跨团队"串知识"。

#### 5. 成本与 ROI 的权衡

| LLM 调用级别               | 单次成本（估算）       | 适用场景                     |
| -------------------------- | ---------------------- | ---------------------------- |
| GPT-4o / Claude Opus       | $0.01~0.05/千 Token    | 复杂归因分析、策略逻辑推理   |
| GPT-4o-mini / Claude Haiku | $0.001~0.005/千 Token  | 数据清洗、格式转换、简单摘要 |
| 本地部署模型 (Qwen/Llama)  | 推理成本低，部署成本高 | 数据不出域场景、高频调用链路 |

**工程策略**：路由分层——简单任务（数据格式化、新闻摘要）用小模型或规则引擎，复杂推理（策略归因、多源融合分析）才调用大模型。这样可以将整体 LLM 调用成本降低 60%~80%，同时保证关键决策的质量。

### 五、对传统量化工作模式的变革意义

#### 1. 从"人找信息"到"信息找人"

传统模式下，研究员每天早上需要手动浏览几十个信息源来"找机会"。Agent 模式下，系统主动将处理好的、个性化的、带有初步分析结论的信息推送过来——研究员从"信息收集者"变成"决策验证者"。

#### 2. 从"单人单策略"到"人机协同研发"

一个资深量化研究员通常同时维护 5~10 个策略已是极限。有了 Agent 辅助后，研究员可以将大量机械化的因子测试、参数优化工作交给 Agent，自己聚焦在高层次的策略逻辑设计上，理论上可以同时跟踪 20~30 个策略线索。

#### 3. 从"经验驱动"到"数据+经验双驱动"

Agent 可以将研究员的历史决策和策略数据向量化存储，在新项目时提供"你三年前做过一个类似的动量策略，当时的结论是..."这类上下文。这让个人经验从"脑子里记"变成了"系统中存"，显著降低知识流失风险。

#### 4. 核心变革不是"替代"而是"倍增"

最重要的一点：Agent 在量化行业的终极价值不是"AI 替代量化研究员"，而是让优秀研究员的产出倍增。一个能驾驭 Agent 工具的研究员，相当于拥有了一个 7×24 小时的助理团队。

### 六、代码示例：一个简化的量化因子研究 Agent

以下是一个基于 LangChain 的简化实现，展示 Agent 如何进行因子挖掘和回测：

```python
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from typing import List, Dict
import pandas as pd
import numpy as np

# ==================== 工具定义 ====================

@tool
def get_factor_pool(category: str) -> List[Dict]:
    """获取因子库中指定类别的候选因子及其历史表现。

    Args:
        category: 因子类别，如 'momentum', 'value', 'volume', 'sentiment'
    """
    factor_db = {
        "momentum": [
            {"name": "ret_20d", "desc": "20日收益率", "ic_mean": 0.035, "ic_ir": 0.62},
            {"name": "ret_60d", "desc": "60日收益率", "ic_mean": 0.028, "ic_ir": 0.48},
            {"name": "rsi_14", "desc": "14日RSI", "ic_mean": -0.018, "ic_ir": 0.35},
        ],
        "volume": [
            {"name": "volume_ratio", "desc": "量比(当日/5日均量)", "ic_mean": 0.022, "ic_ir": 0.41},
            {"name": "turnover_std", "desc": "换手率波动", "ic_mean": 0.015, "ic_ir": 0.28},
            {"name": "vwap_deviation", "desc": "VWAP偏离度", "ic_mean": -0.025, "ic_ir": 0.52},
        ],
        "value": [
            {"name": "pe_ttm", "desc": "市盈率TTM", "ic_mean": -0.032, "ic_ir": 0.55},
            {"name": "pb_lf", "desc": "市净率LF", "ic_mean": -0.028, "ic_ir": 0.49},
        ],
    }
    return factor_db.get(category, [])

@tool
def run_factor_backtest(
    factor_expressions: List[str],
    universe: str = "csi500",
    start_date: str = "2023-01-01",
    end_date: str = "2025-12-31",
    holding_period: int = 5,
) -> Dict:
    """对指定的因子表达式执行回测，返回回测指标。

    Args:
        factor_expressions: 因子表达式列表，如 ['volume_ratio * ret_20d', 'vwap_deviation']
        universe: 股票池，如 'csi300', 'csi500', 'all_a'
        start_date: 回测开始日期
        end_date: 回测结束日期
        holding_period: 持仓周期（交易日）
    """
    # 模拟回测结果（生产环境需对接真实回测引擎）
    np.random.seed(hash(str(factor_expressions)) % 2**31)
    
    # 模拟 IC 分析
    ic_values = np.random.normal(loc=0.03, scale=0.08, size=500)
    
    # 模拟策略收益
    cumulative_returns = np.cumprod(1 + np.random.normal(0.001, 0.015, 500))
    
    metrics = {
        "annual_return": (cumulative_returns[-1] ** (252/500) - 1) * 100,
        "annual_volatility": np.std(np.diff(np.log(cumulative_returns))) * np.sqrt(252) * 100,
        "max_drawdown": max(1 - cumulative_returns[i] / max(cumulative_returns[:i+1]) 
                           for i in range(len(cumulative_returns))) * 100,
        "sharpe_ratio": (np.mean(np.diff(np.log(cumulative_returns))) * 252) / 
                        (np.std(np.diff(np.log(cumulative_returns))) * np.sqrt(252)),
        "ic_mean": np.mean(ic_values),
        "ic_ir": np.mean(ic_values) / np.std(ic_values) if np.std(ic_values) > 0 else 0,
        "turnover_daily_pct": np.random.uniform(15, 40),  # 日换手率
        "win_rate": np.mean(np.diff(np.log(cumulative_returns)) > 0) * 100,
    }
    
    return {
        "factors": factor_expressions,
        "universe": universe,
        "backtest_period": f"{start_date} ~ {end_date}",
        "metrics": metrics,
    }

@tool
def analyze_backtest_result(metrics: Dict) -> str:
    """分析回测结果，给出定性判断和改进建议。

    Args:
        metrics: run_factor_backtest 返回的 metrics 字典
    """
    analysis = []
    m = metrics["metrics"]
    
    # 夏普比率评估
    if m["sharpe_ratio"] > 2.0:
        analysis.append("✓ 夏普比率优秀 (>2.0)，策略风险调整后收益良好")
    elif m["sharpe_ratio"] > 1.0:
        analysis.append("△ 夏普比率中等 (1.0~2.0)，有优化空间")
    else:
        analysis.append("✗ 夏普比率偏低 (<1.0)，需要重新审视策略逻辑")
    
    # IC 评估
    if m["ic_ir"] > 0.5:
        analysis.append("✓ IC_IR > 0.5，因子选股能力显著")
    elif m["ic_ir"] > 0.3:
        analysis.append("△ IC_IR 在 0.3~0.5，因子有一定选股能力但稳定性不足")
    else:
        analysis.append("✗ IC_IR < 0.3，因子选股能力弱，不建议单独使用")
    
    # 换手率评估
    if m["turnover_daily_pct"] > 30:
        analysis.append(f"⚠ 日换手率 {m['turnover_daily_pct']:.1f}%，偏高，需检查实际交易成本是否侵蚀收益")
    
    # 最大回撤
    if m["max_drawdown"] > 20:
        analysis.append(f"⚠ 最大回撤 {m['max_drawdown']:.1f}% 较大，建议加入止损或波动率目标控制")
    
    return "\n".join(analysis)

@tool
def check_compliance(
    position_weights: Dict[str, float],
    max_single_stock: float = 0.10,
    max_industry: float = 0.30,
) -> Dict:
    """合规校验：检查持仓是否满足集中度、行业分布等合规约束。

    Args:
        position_weights: {股票代码: 权重} 字典
        max_single_stock: 单票最大仓位，默认 10%
        max_industry: 单行业最大仓位，默认 30%
    """
    violations = []
    
    for stock, weight in position_weights.items():
        if weight > max_single_stock:
            violations.append(f"单票超限: {stock} 权重 {weight*100:.1f}% > {max_single_stock*100}%")
    
    passed = len(violations) == 0
    return {
        "passed": passed,
        "violations": violations,
        "max_single_stock": max_single_stock,
        "max_industry": max_industry,
    }

# ==================== Agent 组装 ====================

tools = [
    get_factor_pool,
    run_factor_backtest, 
    analyze_backtest_result,
    check_compliance,
]

system_prompt = """你是一个量化因子研究助手 Agent。你的职责是：
1. 理解研究员的策略需求，将其转化为具体的因子选择和组合方案
2. 自主调用工具执行因子检索、回测、分析
3. 根据回测结果提出改进建议，并进入迭代循环
4. 最终输出包含策略代码、回测指标、风险分析和改进建议的完整报告

重要约束：
- 所有数值结论必须来自工具返回的实际数据，严禁凭空编造
- 回测结果中的优秀表现（如高夏普比率）可能来自过拟合，必须提示此风险
- 策略建议必须附带风险提示和合规审查
- 不得给出具体的投资建议或预测未来收益
"""

agent_prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

# 创建 Agent（依赖模型的 Function Calling 能力）
agent = create_tool_calling_agent(llm, tools, agent_prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    max_iterations=8,           # 最多 8 轮迭代，防止无限循环
    handle_parsing_errors=True, # 解析错误时自动重试
    return_intermediate_steps=False,
)

# ==================== 运行示例 ====================

task = """
请帮我挖掘 A 股市场中基于"成交量异动 + 北向资金"的短线因子组合：
- 股票池: 中证500
- 回测期: 2023-01-01 ~ 2025-12-31
- 调仓周期: 5 个交易日
- 单票最大仓位: 10%
要求：先列出候选因子，选择 2~3 个组合回测，根据结果迭代一次，最后给出完整分析报告。
"""

result = agent_executor.invoke({"input": task})
print(result["output"])
```

### 七、行业落地建议与路线图

从团队实际落地的角度，建议采用分阶段推进的策略：

```text
Phase 1（1~2 个月）：非交易链路试点
  └── 研报自动生成 + 信息聚合摘要
  └── 目标：验证 Agent 在量化场景的基本可用性，建立团队信心

Phase 2（2~4 个月）：策略辅助研发
  └── 因子批量回测 + 结果分析 + 策略参数优化建议
  └── 目标：让 1 个研究员能同时跟踪 2 倍的策略线索

Phase 3（4~6 个月）：实时风控助理
  └── 异常监控 + 自动归因 + 合规校验
  └── 目标：将异常事件的首次响应时间从分钟级降到秒级

Phase 4（6+ 个月）：全流程 Agent 协同
  └── 多个专业 Agent 协作（投研/因子/风控/知识管理）
  └── 目标：建成 Agent-native 的量化投研平台
```

每个 Phase 结束时的验收标准：
- Phase 1：研报生成准确率 > 90%（数据引用正确、逻辑通顺、无幻觉）
- Phase 2：Agent 辅助的回测效率高于纯手动操作（时间节省 > 50%）
- Phase 3：异常事件漏报率 < 5%，误报率 < 20%
- Phase 4：整体投研效率提升 > 100%（同等人力产出翻倍）

### 知识扩展

- **Agent 工具调用可靠性 (2.25 节)**：量化场景对工具调用的准确性要求极高——一个错误的数据查询可能导致错误的回测结论。需要从工具描述设计、参数校验、调用链路保障多层面确保可靠性。
- **Agent 的规划-执行-反思闭环 (2.15 节)**：策略研发中的"生成因子 → 回测 → 分析 → 修正"正是典型的规划-执行-反思模式，理解这个闭环的实现机制有助于设计更好的量化 Agent。
- **多 Agent 协作 (2.20 节)**：成熟阶段的量化平台需要多个专业 Agent 协作（投研 Agent、因子 Agent、风控 Agent、知识管理 Agent），需要理解多 Agent 的通信、任务分配和冲突消解机制。
- **Function Calling 与 MCP (11.1~11.5 节)**：量化 Agent 需要调用行情 API、数据库、回测引擎等大量工具，Function Calling 是基础能力，MCP 协议是标准化接入的关键基础设施。
- **RAG 与知识管理 (第 1 章)**：投研知识库的构建依赖 RAG 技术，包括向量检索、混合检索、Rerank 等，Agent 通过 RAG 获取历史研报和策略信息。
- **模型幻觉与事实一致性 (1.8 节)**：量化场景对幻觉零容忍——一个错误的财务数据引用可能引起严重的合规问题。需要从 RAG 幻觉控制的角度建立多层校验机制。
- **Agent 评估 (2.40 节)**：如何评估量化 Agent 的质量？需要建立专门的评估指标体系，包括数据引用准确率、策略建议合理性、风险提示完备性等。

### 完整口头回答

Agent 在量化金融行业的应用可以从四个核心场景来理解。

第一是投研流程自动化。量化研究员大约 60%~70% 的时间花在数据清洗、研报格式调整、会议纪要整理等非核心工作上。Agent 可以自动化这些环节：接收自然语言指令后，自动检索多源数据、调用工具获取行情和财务信息、按研报模板生成结构化报告并自动引用数据来源。这让研究员从"信息收集者"变成"决策验证者"。

第二是多源数据融合分析。量化行业的数据源极其分散——行情、财务、另类数据、舆情、宏观——格式各异、频率不同。Agent 可以通过 Function Calling 动态选择数据源，通过多步推理判断数据质量，在统一语义空间下进行时间对齐、实体关联和跨源交叉验证。比如 Agent 发现卫星图像显示某芯片厂卡车流量骤降后，自动交叉验证供应链订单数据和股价，生成预警报告。

第三是策略生成与迭代。这是 Agent 最有想象力的应用方向。研究员用自然语言描述策略思路后，Agent 自动完成因子检索、表达式生成、回测执行、结果分析和改进建议的全流程。核心工作模式是"研究员提出策略假设 → Agent 负责机械化的实验管理和初步分析 → 研究员在分析结果基础上修正逻辑方向"。Agent 是策略研发的加速器而非替代者。

第四是风险监控与预警。Agent 在两个层面发挥作用：被动层面，持续监控 PnL、回撤、滑点、持仓集中度等指标，异常触发时自动执行多维度归因分析并生成处置建议；主动层面，从政策文件措辞变化、产业链财报电话会中的危险词汇、社交媒体情感突变中预先嗅探风险信号。

落地量化领域面临五个核心挑战。第一是数据时效性与低延迟要求的矛盾——Agent 的 LLM 推理延迟在秒级，适用于日频/周频策略和投研分析，但不适用于高频和日内中频交易。工程上需要把 LLM 放在离线/准实时链路，高频信号由传统规则引擎处理。第二是模型幻觉问题——一个幻觉可能导致错误的因子构建或回测结论，需要通过数据溯源校验、交叉验证、数值型输出 Schema 校验、合规规则引擎二次校验来层层把关。第三是合规的硬约束——Agent 的自主决策特性与金融"可控、可解释、可追溯"的要求存在张力，Agent 绝不应拥有直接下单权限，所有决策需要完整留痕。第四是策略知识产权保护——需要为 Agent 的知识检索设置严格的权限边界。第五是成本控制——需要路由分层，简单任务用小模型或规则引擎，复杂推理才调用大模型。

对传统量化工作模式的变革意义在于：从"人找信息"到"信息找人"，从"单人单策略"到"人机协同研发"，从"经验驱动"到"数据+经验双驱动"。核心变革不是替代而是倍增——让优秀研究员的产出翻倍。



大模型本身是无状态的 (Stateless)，每次推理只能看到当前输入的 Token 序列，带来了两个核心问题：

- 上下文窗口有限：在长对话或大文档场景下不够
- 跨会话遗忘：两次独立调用之间，模型对之前的交互毫无记忆

### 记忆的分类框架

```plaintext
记忆类型
├── 短期记忆 (Short-term Memory)
│   ├── 对话缓冲记忆 (Buffer Memory)
│   └── 摘要记忆 (Summary Memory)
│
└── 长期记忆 (Long-term Memory)
    ├── 向量数据库检索记忆 (Vector Store Memory)
    ├── 结构化存储记忆 (Entity Memory / KG Memory)
    └── 外部工具记忆 (Tool-augmented Memory)
```

### 短期记忆 (Short-term Memory)

短期记忆对应的是 **当前会话内的上下文管理**，直接放在 Prompt 的上下文窗口中。

#### 对话缓冲记忆 (Buffer Memory)

最简单直接的方式：把历史对话的全部内容直接拼接到 Prompt 中。

```plaintext
[System Prompt]
[Human]: 你好，我叫张三
[AI]: 你好，张三！有什么我可以帮你的？
[Human]: 我喜欢打篮球
[AI]: 太棒了！篮球是一项很好的运动...
[Human]: 我叫什么名字？   <-- 当前输入
```

优点：实现简单、信息无损失

缺点：随对话增长，Token 消耗线性增加，最终超出上下文窗口

#### 摘要记忆 (Summary Memory)

当对话过长时，用 LLM 对历史对话进行滚动摘要，只保留摘要而非原文

核心思路：

```plaintext
旧摘要 + 新对话  -->  [LLM 摘要]  -->  新摘要
```

```python
class SummaryMemory:
    def __init__(self, llm_client, summary_threshold: int = 2000):
        """
        滚动摘要记忆
        :param llm_client: LLM 客户端 (用于生成摘要)
        :param summary_threshold: 当历史 token 数超过该阈值时触发摘要
        """
        self.llm = llm_client
        self.summary = ""          # 当前的历史摘要
        self.recent_messages = []  # 最近几轮的原始对话 (尚未被摘要)
        self.threshold = summary_threshold

    def _estimate_tokens(self, text: str) -> int:
        """简单估算 token 数 (实际应用中用 tiktoken 等工具)"""
        return len(text) // 4

    def _should_summarize(self) -> bool:
        """判断是否需要触发摘要"""
        recent_text = " ".join([m["content"] for m in self.recent_messages])
        return self._estimate_tokens(recent_text) > self.threshold

    def _summarize(self):
        """调用 LLM 生成新摘要"""
        recent_text = "\n".join(
            [f"{m['role']}: {m['content']}" for m in self.recent_messages]
        )

        prompt = f"""请将以下对话摘要与新对话合并，生成一个简洁的新摘要，保留关键信息：

已有摘要：
{self.summary}

新对话：
{recent_text}

新摘要："""

        # 调用 LLM 生成摘要 (此处为伪代码，实际需要接入真实 LLM)
        new_summary = self.llm.complete(prompt)

        self.summary = new_summary
        self.recent_messages = []  # 清空已被摘要的原始对话

    def add_message(self, role: str, content: str):
        """添加新消息，必要时触发摘要"""
        self.recent_messages.append({"role": role, "content": content})

        if self._should_summarize():
            self._summarize()

    def get_context(self) -> str:
        """
        获取注入 Prompt 的上下文
        格式: [历史摘要] + [最近原始对话]
        """
        context = ""
        if self.summary:
            context += f"[对话历史摘要]\n{self.summary}\n\n"
        if self.recent_messages:
            context += "[最近对话]\n"
            context += "\n".join(
                [f"{m['role']}: {m['content']}" for m in self.recent_messages]
            )
        return context
```

### 长期记忆 (Long-term Memory)

长期记忆用于跨会话的信息持久化，存储在模型上下文窗口之外的外部系统中，按需检索。

#### 向量数据库记忆

这是目前最主流的长期记忆实现方案，也是 RAG (Retrieval-Augmented Generation) 的核心。

```plaintext
写入阶段 (存储记忆):
信息片段 --> Embedding 模型 --> 向量 --> 向量数据库 (附带原文)

读取阶段 (检索记忆):
当前查询 --> Embedding 模型 --> 查询向量 --> 相似度搜索 --> Top-K 相关记忆 --> 注入 Prompt
```

#### 实体记忆 / 知识图谱记忆 (Entity Memory)

对于需要记忆结构化实体信息的场景 (如用户画像、业务实体关系)，可以使用结构化存储。

```python
# 实体记忆示例：用 JSON 结构化存储用户信息
entity_memory = {
    "用户": {
        "姓名": "张三",
        "年龄": 25,
        "职业": "软件工程师",
        "爱好": ["篮球", "AI", "看电影"],
        "学习偏好": "视频教程 + 实战项目"
    },
    "目标": {
        "短期": "学习深度学习基础",
        "长期": "转型为 AI 工程师"
    }
}

# 在 Prompt 中注入结构化实体信息
def build_entity_prompt(entity_memory: dict) -> str:
    import json
    return f"""[用户已知信息]
{json.dumps(entity_memory, ensure_ascii=False, indent=2)}

请基于以上用户信息提供个性化回答。
"""
```

#### 混合记忆架构 (Hybrid Memory Architecture)

实际生产中，通常组合使用短期 + 长期记忆：

```plaintext
用户输入
    │
    ▼
┌─────────────────────────────────────┐
│           记忆管理器                  │
│                                     │
│  1. 检索长期记忆 (向量数据库)           │
│  2. 获取短期记忆 (对话历史/摘要)        │
│  3. 组装最终 Prompt                  │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│           最终 Prompt 结构            │
│                                     │
│  [System Prompt]                    │
│  [长期记忆: 用户画像/历史知识]          │
│  [短期记忆: 本轮对话摘要/最近N轮]       │
│  [当前用户输入]                       │
└─────────────────────────────────────┘
    │
    ▼
   LLM
    │
    ▼
  输出响应
    │
    ├── 更新短期记忆 (追加到 Buffer/触发摘要)
    └── 异步更新长期记忆 (提取关键信息存入向量库)
```

```python
class HybridMemoryManager:
    """混合记忆管理器：统一调度短期和长期记忆"""

    def __init__(self, short_term: SummaryMemory, long_term: VectorStoreMemory):
        self.short_term = short_term
        self.long_term = long_term

    def build_full_prompt(self, user_input: str, system_prompt: str) -> list:
        """
        构建包含完整记忆上下文的 Prompt
        """
        messages = []

        # 1. System Prompt (角色定义)
        system_content = system_prompt

        # 2. 注入长期记忆 (相关历史信息)
        long_term_context = self.long_term.build_memory_prompt(user_input)
        if long_term_context:
            system_content += f"\n\n{long_term_context}"

        messages.append({"role": "system", "content": system_content})

        # 3. 注入短期记忆 (本轮对话历史)
        short_term_context = self.short_term.get_context()
        if short_term_context:
            # 将摘要作为系统消息注入，避免污染对话流
            messages.append({
                "role": "system", 
                "content": f"[本轮对话上下文]\n{short_term_context}"
            })

        # 4. 当前用户输入
        messages.append({"role": "user", "content": user_input})

        return messages

    def update_memories(self, user_input: str, assistant_response: str):
        """
        对话结束后更新记忆
        """
        # 更新短期记忆
        self.short_term.add_message("user", user_input)
        self.short_term.add_message("assistant", assistant_response)

        # 异步提取关键信息更新长期记忆
        # (实际中可用 LLM 判断是否有值得长期记忆的信息)
        self._async_update_long_term(user_input, assistant_response)

    def _async_update_long_term(self, user_input: str, response: str):
        """
        提取值得长期记忆的关键信息
        (实际实现中可调用 LLM 做信息提取和过滤)
        """
        # 示例：简单规则过滤，实际可用 LLM 做智能提取
        important_keywords = ["我叫", "我是", "我喜欢", "我的目标", "我需要"]
        if any(kw in user_input for kw in important_keywords):
            self.long_term.save_memory(
                content=f"用户说：{user_input}",
                metadata={"type": "user_info"}
            )
```
