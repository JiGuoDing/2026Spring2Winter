# ⚡ LangGraph 5分钟快速开始

> 如果你已经熟悉 Python 和 LangChain，可以直接从这里开始

## 前置检查

- [ ] Python 3.10+ 已安装
- [ ] 已有 OpenAI 或通义千问 API Key
- [ ] 了解 Python 异步编程基础（async/await）

## 第 1 步：安装依赖

```bash
# 进入项目目录
cd LangGraph

# 安装所有依赖
pip install -r requirements.txt
```

验证安装：
```bash
python -c "import langgraph; print(f'LangGraph 版本: {langgraph.__version__}')"
```

## 第 2 步：配置 API Key

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
# Windows: notepad .env
# Mac/Linux: nano .env
```

在 `.env` 文件中填入你的 API Key：
```env
# OpenAI
OPENAI_API_KEY=your-api-key-here

# 或使用通义千问
DASHSCOPE_API_KEY=your-dashscope-key-here
```

## 第 3 步：运行第一个示例

### 示例 1：State 基础示例

```bash
python "01-LangGraph 核心概念/examples/basic_state.py"
```

**你将看到**：State 的创建、更新和 reducer 机制演示

### 示例 2：简单节点图

```bash
python "01-LangGraph 核心概念/examples/simple_node.py"
```

**你将看到**：如何创建节点、添加边、编译和执行图

### 示例 3：条件边

```bash
python "01-LangGraph 核心概念/examples/conditional_edge.py"
```

**你将看到**：如何根据状态动态选择下一个节点

## 第 4 步：运行第一个 Agent

```bash
python "02-第一个 LangGraph Agent/examples/first_agent.py"
```

**你将看到**：
- Agent 接收用户输入
- 模型决定调用工具
- 工具执行并返回结果
- Agent 生成最终回复

## 下一步

现在你已经成功运行了基础示例，接下来：

1. **系统学习**：从 [00-学习准备](00-学习准备/README.md) 开始
2. **深入理解**：阅读 [01-LangGraph 核心概念](01-LangGraph%20核心概念/README.md)
3. **动手实践**：尝试修改示例代码，观察不同效果

## 常见问题

### Q: 安装依赖时出错？
```bash
# 尝试升级 pip
pip install --upgrade pip

# 或使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q: API Key 配置后仍然报错？
```bash
# 检查 .env 文件是否正确加载
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('OPENAI_API_KEY'))"
```

### Q: 示例代码运行卡住？
- 检查网络连接（需要访问 OpenAI/通义千问 API）
- 检查 API Key 是否有效
- 查看控制台错误信息

## 需要帮助？

- 查看 [08-常见问题与调试](08-常见问题与调试/FAQ.md)
- 阅读 [教程索引](教程索引.md) 找到对应章节
- 访问 [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)

---

**祝你学习愉快！** 🎉
