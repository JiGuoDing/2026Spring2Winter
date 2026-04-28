# 💾 03-状态管理与记忆系统

> 掌握 LangGraph 的状态管理和记忆系统实现

## 🎯 本章目标

- 自定义 State Schema 设计
- 使用 Checkpointer 实现状态持久化
- 实现短期记忆（对话历史管理）
- 集成外部存储实现长期记忆

## 📚 学习内容

1. [StateSchema 设计](01_StateSchema_设计.md)
2. [检查点与持久化](02_检查点与持久化.md)
3. [短期记忆实现](03_短期记忆实现.md)
4. [长期记忆集成](04_长期记忆集成.md)

## 💻 示例代码

1. `examples/custom_state.py` - 自定义 State
2. `examples/sqlite_checkpointer.py` - SQLite 持久化
3. `examples/memory_agent.py` - 带记忆的 Agent

## 🔗 前置知识

- 已完成 01、02 章
- 理解 State、Node、Edge 基础

---

**下一步：** 学习如何设计和管理 Agent 的状态！
