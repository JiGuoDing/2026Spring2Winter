# 📖 什么是 LangGraph

> LangGraph 是基于图的 Agent 编排框架，用于构建复杂的状态化 Agent 应用

## 🎯 学习目标

- 理解 LangGraph 是什么
- 了解为什么需要 LangGraph
- 掌握核心概念：State、Node、Edge、Graph
- 理解 LangGraph 与 LangChain 的关系

---

## 1. LangGraph 是什么

### 定义

**LangGraph** 是 LangChain 团队开发的一个开源框架，专门用于构建**有状态的、多步骤的** Agent 应用。它使用**图（Graph）**的概念来编排 Agent 的执行流程。

### 核心思想

将 Agent 的执行流程看作一个**图**：
- **节点（Node）**：执行具体的操作（如调用模型、执行工具）
- **边（Edge）**：定义节点之间的流转关系
- **状态（State）**：在节点之间传递和共享数据

### 简单比喻

想象一个工厂的流水线：
- **原材料** = State（初始输入）
- **工作站** = Node（处理步骤）
- **传送带** = Edge（流程方向）
- **成品** = State（最终输出）

---

## 2. 为什么需要 LangGraph

### 传统 Agent 的问题

使用纯 LangChain 构建 Agent 时，会遇到以下问题：

#### 问题 1：状态管理困难
```python
# ❌ 手动管理状态，容易出错
conversation_history = []
tool_results = {}
user_context = {}

# 状态散落在各个地方，难以维护
```

#### 问题 2：流程控制复杂
```python
# ❌ 复杂的 if-else 控制流程
if need_tool:
    result = call_tool()
    if tool_success:
        response = generate_response(result)
    else:
        retry()
else:
    response = direct_answer()
```

#### 问题 3：难以实现复杂工作流
- 多步骤任务编排困难
- 并行执行难以实现
- 循环和条件分支代码混乱

### LangGraph 的解决方案

#### ✅ 方案 1：统一的状态管理
```python
# ✓ 使用 State 集中管理所有状态
from typing import TypedDict

class AgentState(TypedDict):
    messages: list          # 对话历史
    tool_results: dict      # 工具结果
    user_context: dict      # 用户上下文
```

#### ✅ 方案 2：可视化的流程控制
```python
# ✓ 使用图来定义流程
graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)
graph.add_node("tool", tool_node)
graph.add_conditional_edges("agent", should_use_tool)
graph.add_edge("tool", "agent")
```

#### ✅ 方案 3：支持复杂工作流
- 子图嵌套
- 并行执行
- 循环和中断
- 人类监督

---

## 3. 核心概念图解

### 四大核心概念

```
┌─────────────────────────────────────────┐
│           LangGraph 核心概念             │
├─────────────────────────────────────────┤
│                                         │
│  State（状态）                           │
│  ├─ 数据的容器                           │
│  ├─ 在节点间传递                         │
│  └─ 使用 reducer 更新                    │
│                                         │
│  Node（节点）                            │
│  ├─ 执行具体操作                         │
│  ├─ 接收 State，返回 State 更新          │
│  └─ 可以是函数或类                       │
│                                         │
│  Edge（边）                              │
│  ├─ 定义节点间的流转                     │
│  ├─ 普通边：固定流程                     │
│  └─ 条件边：动态选择                     │
│                                         │
│  Graph（图）                             │
│  ├─ 由 Node 和 Edge 组成                 │
│  ├─ 编译后成为可执行的应用               │
│  └─ 支持 invoke 和 stream                │
│                                         │
└─────────────────────────────────────────┘
```

### 执行流程示例

```
用户输入: "北京今天天气怎么样？"
    ↓
┌──────────────────────────────────────┐
│ State:                                │
│ {                                    │
│   "messages": [用户问题],             │
│   "tool_calls": []                   │
│ }                                    │
└──────────────────────────────────────┘
    ↓
┌─────────────┐
│ Node: Agent │  ← 模型决定需要调用工具
└─────────────┘
    ↓ (条件边：有工具调用)
┌─────────────┐
│ Node: Tool  │  ← 执行天气查询工具
└─────────────┘
    ↓ (普通边：返回 Agent)
┌─────────────┐
│ Node: Agent │  ← 基于工具结果生成回复
└─────────────┘
    ↓ (条件边：无工具调用)
┌─────────────┐
│   END       │  ← 返回最终结果
└─────────────┘
    ↓
最终输出: "北京今天晴天，温度 20-25°C"
```

---

## 4. 与 LangChain 的关系

### LangChain vs LangGraph

| 特性 | LangChain | LangGraph |
|------|-----------|-----------|
| **定位** | LLM 应用开发框架 | Agent 编排框架 |
| **核心** | Chain（链） | Graph（图） |
| **状态管理** | 简单 | 复杂且灵活 |
| **流程控制** | 线性 | 支持循环、分支、并行 |
| **适用场景** | 简单问答、RAG | 复杂 Agent、工作流 |

### 关系说明

```
┌────────────────────────────────────┐
│         LangChain 生态系统          │
├────────────────────────────────────┤
│                                    │
│  LangChain Core                    │
│  ├─ 模型封装 (ChatModel)           │
│  ├─ 提示词管理 (Prompt)            │
│  ├─ 工具系统 (Tools)               │
│  └─ 输出解析 (Output Parser)       │
│                                    │
│  LangGraph (构建在 LangChain 之上) │
│  ├─ 状态管理 (State)               │
│  ├─ 流程编排 (Graph)               │
│  └─ Agent 循环 (ReAct)             │
│                                    │
│  关系：                             │
│  LangGraph 使用 LangChain 的组件   │
│  但提供更强大的流程控制能力         │
│                                    │
└────────────────────────────────────┘
```

### 何时使用 LangGraph

**使用 LangGraph 的场景**：
- ✅ 需要多步骤的 Agent 循环
- ✅ 需要复杂的状态管理
- ✅ 需要人类监督和中断
- ✅ 需要并行执行任务
- ✅ 需要子图和模块化设计

**不需要 LangGraph 的场景**：
- ❌ 简单的单次问答
- ❌ 基本的 RAG 检索（使用 LangChain 即可）
- ❌ 线性的处理流程

---

## 5. 适用场景

### 场景 1：智能客服 Agent
```
用户提问 → 意图识别 → [知识库检索 / 工单创建 / 订单查询] → 生成回复
                        ↓ (可能需要多轮对话)
                   保持对话历史和上下文
```

### 场景 2：数据分析 Agent
```
用户请求 → 解析需求 → [SQL 生成 / 数据查询 / 可视化] → 返回结果
                        ↓ (可能需要多次迭代)
                   缓存中间结果
```

### 场景 3：多步骤工作流
```
接收任务 → 分解步骤 → [步骤1 → 步骤2 → 步骤3] → 汇总结果
                        ↓ (某些步骤可能需要人工审核)
                   中断和继续执行
```

---

## 6. 总结

### 关键点回顾

1. **LangGraph 是什么**：基于图的 Agent 编排框架
2. **为什么需要**：解决状态管理、流程控制、复杂工作流问题
3. **核心概念**：State、Node、Edge、Graph
4. **与 LangChain 的关系**：LangGraph 构建在 LangChain 之上，提供更强大的流程控制

### 下一步

现在你已经理解了 LangGraph 的基本概念，接下来学习：

👉 [State 状态管理 →](02_State_状态管理.md)

---

## 📝 练习题

1. **思考题**：为什么传统的 if-else 不适合复杂的 Agent 流程？
2. **理解题**：用工厂流水线的比喻解释 State、Node、Edge 的关系
3. **应用题**：列举 3 个适合使用 LangGraph 的应用场景

---

## 🔗 参考资源

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [LangGraph GitHub](https://github.com/langchain-ai/langgraph)
- [LangChain 文档](https://python.langchain.com/)
