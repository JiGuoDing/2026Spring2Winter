from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from loguru import logger

model = ChatTongyi(model="qwen3-max")
prompt = ChatPromptTemplate.from_messages([
    ("system", "以我提供的已知参考资料为主，简洁并且专业地回答用户的问题。参考资料：{context}"),
    ("human", "用户提问：{input}")
])

vector_store = InMemoryVectorStore(
    embedding=DashScopeEmbeddings(
        model='text-embedding-v4'
    )
)

# 准备一下资料
# add_texts 传入一个 list[str]
vector_store.add_texts(
    [
        "减肥就是要少吃多练",
        "在减脂期间吃东西很重要，清淡少油控制卡路里摄入并且运动起来",
        "跑步是很好的运动方式",
    ]
)

input_text = "怎么减肥？"

# 检索向量库
result = vector_store.similarity_search(
    query=input_text,
    k=2,
)

reference_text = "["
for doc in result:
    reference_text += f"{doc.page_content}; "
reference_text += "]"

def print_prompt(prompt):
    logger.info(prompt.to_string())
    logger.info("="*20)
    return prompt

# 构建链
chain = prompt | print_prompt | model | StrOutputParser()

res = chain.invoke({"context": reference_text, "input": input_text})

logger.info(res)
