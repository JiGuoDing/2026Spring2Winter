# 🧩 01-LangGraph 核心概念

> 理解 LangGraph 的基础构建块：State、Node、Edge、Graph

## 🎯 本章目标

完成本章后，你将：
- ✅ 理解 LangGraph 是什么以及为什么需要它
- ✅ 掌握 State（状态）的概念和使用方法
- ✅ 学会定义和使用 Node（节点）
- ✅ 理解 Edge（边）的类型和使用场景
- ✅ 能够构建和编译完整的 Graph（图）

## 📚 学习内容

### 1. [什么是 LangGraph](01_什么是%20LangGraph.md)
- LangGraph 的定义和定位
- 为什么需要 LangGraph
- 核心概念图解
- 与 LangChain 的关系

### 2. [State 状态管理](02_State_状态管理.md)
- State 的定义和作用
- TypedDict vs Pydantic
- Reducer 函数
- State 更新机制

### 3. [Node 节点](03_Node_节点.md)
- Node 的定义
- 节点输入输出
- 单节点和多节点
- 节点中的工具调用

### 4. [Edge 边](04_Edge_边.md)
- 普通边（固定流程）
- 条件边（动态选择）
- 并行边（同时执行）
- END 节点

### 5. [Graph 图构建](05_Graph_图构建.md)
- StateGraph 初始化
- 添加节点和边
- 编译和执行
- 完整示例

## 💻 示例代码

本章包含 3 个示例代码：

1. [basic_state.py](examples/basic_state.py) - State 基础示例
2. [simple_node.py](examples/simple_node.py) - 单节点图示例
3. [conditional_edge.py](examples/conditional_edge.py) - 条件边示例

## 🎓 学习路径

```
什么是 LangGraph (概念)
    ↓
State 状态管理 (数据)
    ↓
Node 节点 (处理)
    ↓
Edge 边 (流程)
    ↓
Graph 图构建 (整合)
```

## ⏱️ 预计时间

- 理论阅读：2-3 小时
- 代码实践：1-2 小时
- 练习完成：1 小时

**总计：约 4-6 小时**

## 💡 学习建议

1. **先理解概念**：不要急于写代码，先理解每个概念的作用
2. **动手实践**：每个示例都要亲自运行和修改
3. **画图理解**：用纸笔画出图的执行流程
4. **完成练习**：每节文档末尾的练习题务必完成

## 🔗 前置知识

- 已完成 [00-学习准备](../00-学习准备/README.md)
- 环境已正确配置
- 了解 Python 基础语法

## 🚀 快速开始

```bash
# 运行第一个示例
python "examples/basic_state.py"

# 运行第二个示例
python "examples/simple_node.py"

# 运行第三个示例
python "examples/conditional_edge.py"
```

## ❓ 遇到问题？

- 查看 [08-常见问题与调试](../08-常见问题与调试/FAQ.md)
- 访问 [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)

---

**准备好了吗？让我们开始学习 LangGraph 的核心概念！** 🚀

下一步：[什么是 LangGraph →](01_什么是%20LangGraph.md)
