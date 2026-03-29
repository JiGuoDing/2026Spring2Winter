from openai import OpenAI

# 1. 获取 client 对象
client = OpenAI(
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# 2. 调用模型
client.chat.completions.create(
    model="qwen3.5-plus",
    messages=[
        {"role": "system", "content": "你是一个 Python 编程专家，并且不说废话回答简洁"},
        {"role": "assistant", "content": "好的，我是 Python 编程专家，并且话不多，你要问什么？"}
    ]
)

# 3. 处理结果
