# 第二章：核心 API 使用

## 2.1 Chat Completion API

### 基础用法

```python
from openai import OpenAI

client = OpenAI()

response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "你是一个有帮助的助手"},
        {"role": "user", "content": "你好"}
    ]
)

print(response.choices[0].message.content)
```

### 消息角色说明

- **system**: 设定 AI 的行为和角色
- **user**: 用户的消息
- **assistant**: AI 的回复（用于多轮对话）

### 高级参数

```python
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "user", "content": "写一首关于春天的诗"}
    ],
    temperature=0.7,      # 创造性 (0-2)
    max_tokens=500,       # 最大输出长度
    top_p=1.0,            # 核采样
    frequency_penalty=0,  # 频率惩罚
    presence_penalty=0,   # 存在惩罚
    n=1,                  # 生成几个回答
    stop=["END"]          # 停止词
)
```

### 参数详解

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| temperature | float | 1.0 | 控制随机性，越高越有创意 |
| max_tokens | int | inf | 生成的最大 token 数 |
| top_p | float | 1.0 | 核采样阈值 |
| frequency_penalty | float | 0 | 降低重复度 |
| presence_penalty | float | 0 | 鼓励新话题 |
| n | int | 1 | 生成几个选择 |
| stop | list/str | null | 停止词 |

## 2.2 流式响应（Streaming）

### 同步流式

```python
from openai import OpenAI

client = OpenAI()

stream = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "讲一个故事"}],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content is not None:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

### 异步流式

```python
import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI()

async def chat():
    stream = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "讲一个故事"}],
        stream=True
    )
    
    async for chunk in stream:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)

asyncio.run(chat())
```

### 流式响应处理类

```python
class StreamHandler:
    def __init__(self):
        self.full_response = ""
    
    def on_chunk(self, chunk):
        content = chunk.choices[0].delta.content or ""
        self.full_response += content
        print(content, end="", flush=True)
    
    def on_complete(self):
        print("\n" + "="*50)
        print(f"完整回复：{self.full_response}")

# 使用
handler = StreamHandler()
stream = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello"}],
    stream=True
)

for chunk in stream:
    handler.on_chunk(chunk)
handler.on_complete()
```

## 2.3 Function Calling（工具调用）

### 定义函数

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取某个城市的天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "城市名称"
                    }
                },
                "required": ["location"]
            }
        }
    }
]
```

### 调用函数

```python
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "北京天气怎么样？"}],
    tools=tools
)

# 检查是否需要调用函数
if response.choices[0].message.tool_calls:
    tool_call = response.choices[0].message.tool_calls[0]
    function_name = tool_call.function.name
    arguments = json.loads(tool_call.function.arguments)
    
    print(f"调用函数：{function_name}")
    print(f"参数：{arguments}")
```

### 执行并返回结果

```python
def get_weather(location):
    return f"{location}的天气晴朗，温度 25°C"

# 第一次调用
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "北京天气怎么样？"}],
    tools=tools
)

# 添加工具响应
tool_message = {
    "role": "tool",
    "tool_call_id": response.choices[0].message.tool_calls[0].id,
    "content": get_weather("北京")
}

# 第二次调用获取最终回复
final_response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "user", "content": "北京天气怎么样？"},
        response.choices[0].message,
        tool_message
    ]
)

print(final_response.choices[0].message.content)
```

## 2.4 Embeddings API

### 文本嵌入

```python
response = client.embeddings.create(
    model="text-embedding-ada-002",
    input="你好，世界"
)

embedding = response.data[0].embedding
print(f"向量维度：{len(embedding)}")
```

### 批量嵌入

```python
texts = ["文本 1", "文本 2", "文本 3"]

response = client.embeddings.create(
    model="text-embedding-ada-002",
    input=texts
)

for i, data in enumerate(response.data):
    print(f"文本{i}的嵌入：{data.embedding[:10]}...")  # 只显示前 10 个维度
```

### 应用场景

```python
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def get_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    return response.data[0].embedding

# 计算相似度
text1 = "我喜欢编程"
text2 = "我热爱编码"

emb1 = get_embedding(text1)
emb2 = get_embedding(text2)

similarity = cosine_similarity([emb1], [emb2])[0][0]
print(f"相似度：{similarity}")
```

## 2.5 Images API（DALL-E）

### 生成图片

```python
response = client.images.generate(
    model="dall-e-3",
    prompt="一只在太空中飞行的猫",
    n=1,
    size="1024x1024"
)

image_url = response.data[0].url
print(f"图片 URL: {image_url}")
```

### 编辑图片

```python
response = client.images.edit(
    image=open("original.png", "rb"),
    mask=open("mask.png", "rb"),
    prompt="添加一个太阳",
    n=1,
    size="1024x1024"
)
```

## 2.6 Audio API（Whisper）

### 语音转文字

```python
audio_file = open("speech.mp3", "rb")
transcript = client.audio.transcriptions.create(
    model="whisper-1",
    file=audio_file
)
print(transcript.text)
```

### 语音合成

```python
response = client.audio.speech.create(
    model="tts-1",
    voice="alloy",
    input="你好，这是语音合成示例"
)

response.stream_to_file("output.mp3")
```

## 练习题

1. 实现一个支持多轮对话的程序
2. 使用流式输出来展示回复
3. 创建一个自定义工具并调用
4. 使用 Embeddings 计算文本相似度

## 下一步

学习完核心 API 后，继续学习 [Agent 开发实战](../03-Agent 开发实战/README.md)
