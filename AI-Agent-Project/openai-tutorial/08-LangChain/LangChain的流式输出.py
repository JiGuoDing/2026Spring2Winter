from langchain_community.llms.tongyi import Tongyi

model = Tongyi(model="qwen-max")

# 通过 stream 方法获得流式输出
res = model.stream(input="你是谁？")

for chunk in res:
    print(
        chunk,
        # 每一段之间以空格分隔
        end="",
        # 立刻刷新缓冲区
        flush=True
    )