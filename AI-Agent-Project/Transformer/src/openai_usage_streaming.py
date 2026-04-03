from openai import OpenAI

# 1. 获取 client 对象
client = OpenAI(
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# 2. 调用模型
response = client.chat.completions.create(
    model="qwen3.5-plus",
    messages=[
        {"role": "system", "content": "你是一个 Python 编程专家，并且语言非常严谨"},
        {"role": "assistant", "content": "好的，我是 Python 编程专家，并且语言很严谨，你要问什么？"},
        {"role": "user", "content": "如何使用 Python 创建一个简单的 Web 服务器？"}
    ],
    stream=True # 启用流式返回
)

# 3. 处理结果
# print(response.choices[0].message.content)
for chunk in response:
    print(chunk.choices[0].delta.content,
        end="", # 每一段之间以空格分隔，默认为回车符分隔
        flush=True # 立刻刷新缓冲区
    )
