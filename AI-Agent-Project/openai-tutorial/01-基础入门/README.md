# 第一章：基础入门

## 1.1 环境安装与配置

### 安装 OpenAI Python SDK

```bash
# 使用 pip 安装
pip install openai

# 或者使用 pip3
pip3 install openai

# 指定版本安装（推荐）
pip install "openai>=1.0.0"
```

### 验证安装

```python
import openai
print(openai.__version__)
```

### 依赖要求

- Python 3.7 或更高版本
- requests 库
- tqdm 库
- aiohttp 库（异步支持）

## 1.2 API Key 管理

### 获取 API Key

1. 访问 [OpenAI Platform](https://platform.openai.com/)
2. 登录或注册账号
3. 进入 API Keys 页面
4. 创建新的 API Key

### 设置 API Key

#### 方法一：环境变量（推荐）

```bash
# Linux/Mac
export OPENAI_API_KEY='sk-...'

# Windows PowerShell
$env:OPENAI_API_KEY='sk-...'

# Windows CMD
set OPENAI_API_KEY=sk-...
```

#### 方法二：代码中设置

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-..."  # 不推荐硬编码在代码中
)
```

#### 方法三：配置文件

创建 `.env` 文件：
```
OPENAI_API_KEY=sk-...
```

使用 python-dotenv 加载：
```python
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
```

### API Key 安全最佳实践

⚠️ **重要提醒**：
- ❌ 不要将 API Key 提交到 Git
- ❌ 不要在客户端代码中使用
- ✅ 使用环境变量管理
- ✅ 定期轮换 API Key
- ✅ 监控使用情况

## 1.3 初始化客户端

### 同步客户端

```python
from openai import OpenAI

client = OpenAI()
# 自动从环境变量读取 API Key
```

### 异步客户端

```python
from openai import AsyncOpenAI

client = AsyncOpenAI()
```

### 自定义配置

```python
from openai import OpenAI

client = OpenAI(
    api_key="your-api-key",
    organization="org-xxx",  # 可选，组织 ID
    project="proj-xxx",      # 可选，项目 ID
    base_url="https://api.example.com",  # 可选，自定义代理
    timeout=30.0,  # 超时时间（秒）
    max_retries=3,  # 最大重试次数
)
```

## 1.4 第一个 AI 应用

### Hello World 示例

```python
from openai import OpenAI

client = OpenAI()

response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "user", "content": "你好，请介绍一下自己"}
    ]
)

print(response.choices[0].message.content)
```

### 理解响应对象

```python
response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello!"}]
)

# 查看完整响应
print(response)

# 获取回复内容
content = response.choices[0].message.content
print(content)

# 查看使用量
usage = response.usage
print(f"输入 tokens: {usage.prompt_tokens}")
print(f"输出 tokens: {usage.completion_tokens}")
print(f"总 tokens: {usage.total_tokens}")
```

## 1.5 常用模型介绍

### GPT-4 系列

- `gpt-4`: 最强大的模型，适合复杂任务
- `gpt-4-turbo`: 更快更便宜
- `gpt-4o`: 优化版本，性价比高

### GPT-3.5 系列

- `gpt-3.5-turbo`: 快速且经济，适合大多数场景
- `gpt-3.5-turbo-16k`: 支持更长上下文

### 选择建议

- 🎯 **简单任务**: gpt-3.5-turbo
- 🎯 **复杂推理**: gpt-4
- 🎯 **长文档处理**: gpt-4-turbo 或 gpt-3.5-turbo-16k
- 🎯 **生产环境**: 根据成本和性能平衡选择

## 1.6 错误处理基础

```python
from openai import OpenAI, APIError, RateLimitError, AuthenticationError

client = OpenAI()

try:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello"}]
    )
    print(response.choices[0].message.content)
    
except AuthenticationError:
    print("API Key 无效")
    
except RateLimitError:
    print("请求频率超限")
    
except APIError as e:
    print(f"API 错误：{e}")
    
except Exception as e:
    print(f"未知错误：{e}")
```

## 练习题

1. 成功安装 OpenAI 库并打印版本号
2. 配置 API Key 到环境变量
3. 编写第一个对话程序
4. 实现基础的错误处理

## 下一步

完成基础入门后，继续学习 [核心 API 使用](../02-核心 API 使用/README.md)
