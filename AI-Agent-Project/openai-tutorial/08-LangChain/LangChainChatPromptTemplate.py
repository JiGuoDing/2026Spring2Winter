from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_models.tongyi import ChatTongyi

chat_prompt_template = ChatPromptTemplate.from_messages(
    [
        ("system", "你是一个专业的翻译"),
        MessagesPlaceholder("history"),
        ("human", "翻译以下文本: Actions speak louder than words."),
    ]
)

history_data = [
    ("human", "翻译以下文本: black sheep"),
    ("assistant", "害群之马"),
    ("human", "继续翻译以下文本: Every dog has its day."),
    ("assistant", "谁过年不吃顿饺子"),
]

# * 只有 invoke 方法支持 MessagePlaceholder 注入
# StringPromptValue 通过 to_string 方法转换为字符串
prompt_text = chat_prompt_template.invoke({"history": history_data}).to_string()

print(prompt_text)

model = ChatTongyi(model="qwen3-max")

res = model.invoke(prompt_text)

print(res.content, type(res))