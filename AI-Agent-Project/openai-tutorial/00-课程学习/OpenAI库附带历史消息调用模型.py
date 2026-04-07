from openai import OpenAI

client = OpenAI(
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

response = client.chat.completions.create(
    model="qwen3-max",
    messages=[
        {"role": "system", "content": "你是一个 AI 助理，回答很简洁"},
        {"role": "user", "content": "小明有 2 条宠物狗"},
        {"role": "assistant", "content": "好的"},
        {"role": "user", "content": "小红有 3 条宠物猫"},
        {"role": "assistant", "content": "好的"},
        {"role": "user", "content": "总共有多少条宠物？"}
    ],
    stream=True
)

for chunk in response:
    print(
        chunk.choices[0].delta.content,
        # 每一段之间以空格分隔
        end="",
        # 立刻刷新缓冲区
        flush=True
    )