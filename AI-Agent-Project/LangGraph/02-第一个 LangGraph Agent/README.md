# 🤖 02-第一个 LangGraph Agent

> 从零开始构建你的第一个完整 LangGraph Agent

## 🎯 本章目标

完成本章后，你将：
- ✅ 理解 Agent 的架构设计模式
- ✅ 掌握工具的定义、注册和绑定
- ✅ 学会使用消息系统
- ✅ 能够独立构建完整的 LangGraph Agent
- ✅ 理解 Agent 循环（ReAct 模式）

## 📚 学习内容

### 1. [Agent 架构设计](01_Agent_架构设计.md)
- ReAct 模式详解
- Agent 循环：思考 → 行动 → 观察
- 工具调用循环
- 最大迭代次数控制

### 2. [工具定义与注册](02_工具定义与注册.md)
- @tool 装饰器
- 工具描述的重要性
- 参数类型注解
- 工具绑定到模型

### 3. [消息系统详解](03_消息系统详解.md)
- HumanMessage、AIMessage、SystemMessage
- ToolMessage
- 消息历史管理
- 消息格式规范

### 4. [完整 Agent 实现](04_完整%20Agent%20实现.md)
- State 设计
- 节点设计
- 条件边实现
- 完整代码示例

## 💻 示例代码

1. [tool_definition.py](examples/tool_definition.py) - 工具定义示例
2. [message_system.py](examples/message_system.py) - 消息系统示例
3. [first_agent.py](examples/first_agent.py) - 第一个完整 Agent

## 🎓 学习路径

```
Agent 架构设计 (理论)
    ↓
工具定义与注册 (工具)
    ↓
消息系统 (通信)
    ↓
完整 Agent 实现 (整合)
```

## ⏱️ 预计时间

- 理论阅读：2-3 小时
- 代码实践：2-3 小时
- 练习完成：1-2 小时

**总计：约 5-8 小时**

## 🔗 前置知识

- 已完成 [01-LangGraph 核心概念](../01-LangGraph%20核心概念/README.md)
- 理解 State、Node、Edge、Graph
- 环境已正确配置

## 🚀 快速开始

```bash
# 运行完整 Agent 示例
python "examples/first_agent.py"
```

---

**准备好了吗？让我们开始构建第一个 Agent！** 🚀

下一步：[Agent 架构设计 →](01_Agent_架构设计.md)
