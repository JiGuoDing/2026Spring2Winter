# ❓ 常见问题解答（FAQ）

> 汇总学习过程中最常见的问题和解决方案

---

## 📦 安装配置问题

### Q1: 安装 langgraph 失败

**问题**：
```bash
pip install langgraph
# 报错：Could not find a version that satisfies the requirement
```

**解决方案**：
```bash
# 1. 升级 pip
python -m pip install --upgrade pip

# 2. 使用国内镜像
pip install langgraph -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 检查 Python 版本（需要 3.10+）
python --version
```

### Q2: 导入模块失败

**问题**：
```python
import langgraph
# ModuleNotFoundError: No module named 'langgraph'
```

**解决方案**：
1. 确认虚拟环境已激活
2. 重新安装：`pip install -r requirements.txt`
3. 检查 Python 路径：`which python` 或 `where python`

### Q3: API Key 配置后仍报错

**问题**：
```
openai.OpenAIError: The api_key client option must be set
```

**解决方案**：
```python
# 1. 检查 .env 文件是否存在
# 2. 确认代码中有 load_dotenv()
from dotenv import load_dotenv
load_dotenv()

# 3. 手动测试
import os
print(os.getenv('OPENAI_API_KEY'))

# 4. 重启 Python 进程
```

---

## 🔧 运行错误

### Q4: State 更新不生效

**问题**：
节点返回的 State 更新没有生效

**原因**：
- 没有正确使用 reducer
- 返回格式错误

**解决方案**：
```python
# ❌ 错误：返回完整 State
def node(state):
    return {"message": "new", "count": 1, "history": []}

# ✓ 正确：只返回更新的字段
def node(state):
    return {"message": "new"}  # 其他字段保持不变

# ✓ 使用 reducer
from typing import Annotated
from operator import add

class State(TypedDict):
    messages: Annotated[list, add]  # 追加模式

def node(state):
    return {"messages": [new_message]}  # 会自动追加
```

### Q5: 工具调用失败

**问题**：
```
ToolExecutionError: Tool execution failed
```

**解决方案**：
```python
# 1. 检查工具是否正确定义
@tool
def my_tool(param: str) -> str:
    """工具描述（必须有）"""
    return result

# 2. 检查工具是否绑定到模型
model = model.bind_tools([my_tool])

# 3. 添加工具到 ToolNode
from langgraph.prebuilt import ToolNode
tool_node = ToolNode([my_tool])

# 4. 检查工具描述是否清晰
# 描述会影响模型是否能正确选择工具
```

### Q6: 消息格式错误

**问题**：
```
ValidationError: Message format invalid
```

**解决方案**：
```python
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# ✓ 正确的消息格式
messages = [
    SystemMessage(content="你是助手"),
    HumanMessage(content="你好"),
    AIMessage(content="你好！有什么可以帮助你的？")
]

# ❌ 错误：使用字典
messages = [
    {"role": "system", "content": "你是助手"}  # LangGraph 不使用这种格式
]
```

---

## 🚀 性能问题

### Q7: 响应速度很慢

**原因**：
- 模型 API 调用慢
- 工具执行慢
- 网络延迟

**解决方案**：
```python
# 1. 使用更快的模型
model = ChatOpenAI(model="gpt-3.5-turbo")  # 比 gpt-4 快

# 2. 实现缓存
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_tool(param):
    return result

# 3. 并行执行（如果可能）
# 使用异步节点
async def async_node(state):
    results = await asyncio.gather(
        tool1.invoke(),
        tool2.invoke()
    )
    return {"results": results}

# 4. 检查网络
# 使用国内模型提供商（如通义千问）
```

### Q8: Token 使用过多

**原因**：
- 消息历史太长
- 提示词过长
- 没有截断历史

**解决方案**：
```python
# 1. 限制消息历史
def trim_messages(messages, max_messages=10):
    """只保留最近的消息"""
    if len(messages) > max_messages:
        return messages[-max_messages:]
    return messages

# 2. 使用 Token 计数
import tiktoken

def count_tokens(messages):
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    text = " ".join([m.content for m in messages])
    return len(encoding.encode(text))

# 3. 在 State 中实现自动截断
class State(TypedDict):
    messages: Annotated[list, add]

def agent_node(state):
    # 自动截断
    messages = trim_messages(state["messages"])
    return {"messages": model.invoke(messages)}
```

---

## 🐛 调试技巧

### Q9: 如何调试 Agent？

**方法 1：打印调试**
```python
def agent_node(state):
    print(f"输入 State: {state}")
    response = model.invoke(state["messages"])
    print(f"模型响应: {response}")
    return {"messages": [response]}
```

**方法 2：使用 Stream**
```python
# 查看每一步的执行
for event in app.stream(initial_state):
    print(f"事件: {event}")
```

**方法 3：LangSmith**
```python
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "your-key"

# 在 LangSmith 平台查看执行过程
# https://smith.langchain.com/
```

### Q10: 如何检查 State？

**方法**：
```python
# 1. 在节点中打印
def node(state):
    print(f"当前 State: {state}")
    return {...}

# 2. 使用 stream 查看中间状态
for event in app.stream(initial_state):
    for node_name, output in event.items():
        print(f"节点 {node_name} 输出: {output}")

# 3. 检查最终结果
result = app.invoke(initial_state)
print(f"最终 State: {result}")
```

---

## 💡 最佳实践

### Q11: 如何组织项目结构？

**推荐结构**：
```
my_agent/
├── agent/
│   ├── __init__.py
│   ├── graph.py      # 图定义
│   ├── nodes.py      # 节点函数
│   └── state.py      # State 定义
├── tools/
│   ├── __init__.py
│   └── my_tools.py   # 工具定义
├── config/
│   └── config.yaml   # 配置文件
├── utils/
│   └── helpers.py    # 工具函数
├── .env              # 环境变量
├── requirements.txt  # 依赖
└── main.py           # 入口
```

### Q12: 如何处理错误？

**方案**：
```python
# 1. 工具中添加错误处理
@tool
def my_tool(param: str) -> str:
    """工具描述"""
    try:
        result = do_something(param)
        return f"成功: {result}"
    except Exception as e:
        return f"错误: {str(e)}"

# 2. 节点中添加重试
from tenacity import retry, stop_after_attempt

@retry(stop=stop_after_attempt(3))
def agent_node(state):
    return model.invoke(state["messages"])

# 3. 图级别错误处理
try:
    result = app.invoke(initial_state)
except Exception as e:
    print(f"图执行失败: {e}")
```

---

## 📞 获取更多帮助

如果以上方法无法解决你的问题：

1. **查看官方文档**: https://langchain-ai.github.io/langgraph/
2. **搜索 GitHub Issues**: https://github.com/langchain-ai/langgraph/issues
3. **加入 Discord 社区**: https://discord.gg/langchain
4. **查看本教程的 08 章节**: 调试技巧指南

---

**问题解决了？继续学习下一章吧！** 🚀
