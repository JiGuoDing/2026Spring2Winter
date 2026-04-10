from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

# 得到模型对象，qwen3-max 是聊天模型
model = ChatTongyi(model="qwen3-max")

# 准备消息列表
messages = [
    # (角色, 内容)，角色只能是 system、human、ai 三种，分别代表系统消息、人类消息、AI 消息
    ("system", "你是一个抒情诗人"),
    ("human", "写一首唐诗"),
    ("ai", "锄禾日当午，汗滴禾下土。谁知盘中餐，粒粒皆辛苦。"),
    ("human", "模仿你上一个回复的格式，再写一首唐诗")
]

# * 简写的好处在于其支持哪部填充{变量}占位，可以运行时填充具体值

# 调用 stream 流式执行
res = model.stream(input=messages)

for chunk in res:
    print(chunk.content, end="", flush=True)