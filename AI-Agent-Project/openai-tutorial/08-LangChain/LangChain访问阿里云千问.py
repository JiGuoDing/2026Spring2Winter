from langchain_community.llms.tongyi import Tongyi

# 不用 qwen3-max，因为 qwen3-max 是聊天模型，qwen-max 是大语言模型
model = Tongyi(model="qwen-max")

# 调用 invoke 向模型提问
res = model.invoke(input="你是谁？")

print(res)