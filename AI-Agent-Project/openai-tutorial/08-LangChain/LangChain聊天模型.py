from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

# 得到模型对象，qwen3-max 是聊天模型
model = ChatTongyi(model="qwen3-max")

# 准备消息列表
messages = [
    SystemMessage(content="你是一个抒情诗人"),
    HumanMessage(content="写一首唐诗")
]

# 调用 stream 流式执行
res = model.stream(input=messages)

for chunk in res:
    print(chunk.content, end="", flush=True)