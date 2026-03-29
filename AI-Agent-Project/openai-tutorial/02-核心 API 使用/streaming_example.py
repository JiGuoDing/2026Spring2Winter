from openai import OpenAI

client = OpenAI()

# 流式响应示例
stream = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "讲一个简短的故事"}],
    stream=True
)

print("流式输出：")
for chunk in stream:
    if chunk.choices[0].delta.content is not None:
        print(chunk.choices[0].delta.content, end="", flush=True)

print("\n\n完成！")
