from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_models.tongyi import ChatTongyi

chat_prompt_template = ChatPromptTemplate.from_messages(
    [
        ("system", "你是一个专业的翻译"),
        MessagesPlaceholder("history"),
        ("human", "翻译以下文本: Actions speak louder than words."),
    ]
)

# 要注入的历史数据
history_data = [
    ("human", "翻译以下文本: black sheep"),
    ("assistant", "害群之马"),
    ("human", "继续翻译以下文本: Every dog has its day."),
    ("assistant", "谁过年不吃顿饺子"),
]

model = ChatTongyi(model="qwen3-max")

# * 组成链要求所有组件都是 Runnable 接口的子类
# * 前一个的输出作为下一个的输入
chain = chat_prompt_template | model

# * 通过链去调用 invoke 或 stream
# res = chain.invoke({"history": history_data})
# print(res.content)

for chunk in chain.stream({"history": history_data}):
    # print(type(chunk))

    print(chunk.content, end="", flush=True)