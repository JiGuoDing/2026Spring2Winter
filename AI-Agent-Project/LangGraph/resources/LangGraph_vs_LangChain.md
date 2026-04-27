# ⚖️ LangGraph vs LangChain 对比分析

> 理解两个框架的定位、区别和使用场景

---

## 📊 快速对比表

| 特性 | LangChain | LangGraph |
|------|-----------|-----------|
| **定位** | LLM 应用开发框架 | Agent 编排框架 |
| **核心抽象** | Chain（链） | Graph（图） |
| **流程控制** | 线性 | 支持循环、分支、并行 |
| **状态管理** | 简单 | 复杂且灵活 |
| **学习曲线** | 较低 | 较高 |
| **适用场景** | 简单问答、RAG | 复杂 Agent、工作流 |

---

## 🎯 定位差异

### LangChain：LLM 应用开发的基础设施

**核心功能**：
- 模型封装（ChatModel、LLM）
- 提示词管理（PromptTemplate）
- 工具系统（Tools）
- 输出解析（Output Parser）
- 链式调用（Chain）
- 文档加载（Document Loader）
- 向量存储（Vector Store）

**设计哲学**：
```
输入 → [处理步骤 1] → [处理步骤 2] → ... → 输出
```

**适合场景**：
- 简单的问答系统
- RAG 检索增强
- 文本转换任务
- 一次性的 API 调用

### LangGraph：复杂 Agent 的编排框架

**核心功能**：
- 状态管理（State）
- 节点定义（Node）
- 流程控制（Edge）
- 图编译（Graph）
- 持久化（Checkpoint）
- 流式输出（Stream）
- 人类监督（Interrupt）

**设计哲学**：
```
      ┌─────────────────┐
      ↓                 │
输入 → [节点 1] → [节点 2] → ... → 输出
      ↓                 ↑
      └─────────────────┘
      （支持循环和分支）
```

**适合场景**：
- 多轮对话 Agent
- 需要状态管理的应用
- 复杂工作流编排
- 需要人类监督的场景
- 并行任务执行

---

## 🔄 关系说明

### LangGraph 构建在 LangChain 之上

```
┌──────────────────────────────────────┐
│          LangChain Core              │
│  ├─ ChatModel（模型封装）            │
│  ├─ PromptTemplate（提示词）         │
│  ├─ Tools（工具）                    │
│  └─ OutputParser（输出解析）         │
└──────────────────────────────────────┘
                ↓ 使用
┌──────────────────────────────────────┐
│          LangGraph                    │
│  ├─ State（状态管理）                │
│  ├─ Node（节点）                     │
│  ├─ Edge（流程控制）                 │
│  └─ Graph（图编排）                  │
└──────────────────────────────────────┘
```

**关键点**：
- LangGraph 不是替代 LangChain，而是补充
- LangGraph 使用 LangChain 的组件（模型、工具等）
- LangGraph 提供更强大的流程控制能力

---

## 💻 代码对比

### 场景：简单的问答系统

#### 使用 LangChain
```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# 简单直接
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个助手"),
    ("human", "{question}")
])

chain = prompt | ChatOpenAI()
response = chain.invoke({"question": "你好"})
```

**优势**：简单、直接  
**劣势**：无法处理复杂流程

### 场景：需要工具调用的 Agent

#### 使用 LangChain（复杂）
```python
from langchain.agents import create_openai_tools_agent

# 状态管理困难
# 流程控制复杂
# 难以实现循环和分支
```

#### 使用 LangGraph（优雅）
```python
from langgraph.graph import StateGraph, END

class State(TypedDict):
    messages: Annotated[List, add]

def agent_node(state):
    # 调用模型
    return {"messages": [model.invoke(state["messages"])]}

def should_use_tool(state):
    # 条件判断
    return "tools" if has_tool_calls else "end"

graph = StateGraph(State)
graph.add_node("agent", agent_node)
graph.add_conditional_edges("agent", should_use_tool)
app = graph.compile()
```

**优势**：状态清晰、流程可控  
**劣势**：学习成本较高

---

## 🤔 如何选择

### 选择 LangChain 的情况

✅ **使用 LangChain 当**：
1. 只需要简单的问答系统
2. 实现基本的 RAG 检索
3. 文本转换任务（翻译、摘要等）
4. 一次性的 API 调用
5. 快速原型验证

**典型项目**：
- 客服问答系统
- 文档摘要生成
- 代码翻译工具
- 简单的聊天机器人

### 选择 LangGraph 的情况

✅ **使用 LangGraph 当**：
1. 需要多轮对话管理
2. 需要复杂的状态管理
3. 需要工具调用循环
4. 需要人类监督和中断
5. 需要并行执行任务
6. 需要子图和模块化设计

**典型项目**：
- 智能客服 Agent（多轮对话）
- 数据分析 Agent（多次迭代）
- 工作流编排（复杂流程）
- 审批系统（人类监督）
- 多步骤任务（并行执行）

---

## 🎓 学习建议

### 初学者路线

```
1. 先学习 LangChain 基础
   ├─ 模型调用
   ├─ 提示词管理
   └─ 工具系统

2. 再学习 LangGraph
   ├─ State、Node、Edge
   ├─ Agent 循环
   └─ 高级功能

3. 实际项目中结合使用
   ├─ LangChain 提供组件
   └─ LangGraph 负责编排
```

### 实际开发模式

```python
# 使用 LangChain 的组件
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

# 使用 LangGraph 编排
from langgraph.graph import StateGraph

model = ChatOpenAI()  # LangChain

@tool  # LangChain
def my_tool():
    pass

graph = StateGraph(State)  # LangGraph
graph.add_node("agent", lambda s: {"messages": [model.invoke(s["messages"])]})
```

---

## 📝 总结

### LangChain
- **定位**：LLM 应用开发的基础设施
- **优势**：组件丰富、易于上手
- **劣势**：流程控制能力有限
- **适用**：简单任务、快速开发

### LangGraph
- **定位**：复杂 Agent 的编排框架
- **优势**：流程可控、状态管理强大
- **劣势**：学习曲线较陡
- **适用**：复杂 Agent、工作流

### 最佳实践
- **不要二选一**：两者结合使用
- **根据场景选择**：简单任务用 LangChain，复杂流程用 LangGraph
- **渐进式学习**：先学 LangChain，再学 LangGraph

---

**理解了两者的区别，就能更好地选择和使用！** 🚀
