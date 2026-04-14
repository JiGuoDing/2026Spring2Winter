from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
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

# * 将向量检索的过程也入链
# * 由于 InMemoryVectorStore 不是 Runnable 的子类，因此无法直接入链
# * langchain 中向量存储对象有一个方法 as_retriever，可以将向量存储对象转换为一个可入链的检索器 (返回一个 Runnable 接口的子类实例对象)
# * k: 2 表示返回相似度最高的 2 条记录
retriever = vector_store.as_retriever(search_kwargs={"k": 2})

# ! 按照以下顺序构建链是不正确的，输入和输出类型不匹配
chain = retriever | prompt | model | StrOutputParser()
'''
retriever:
    - 输入：用户的 prompt   str
    - 输出：向量库的检索结果    list[Document] (同时这里丢失了用户的 prompt)
prompt:
    - 输入：用户的 prompt + 向量库的检索结果    dict
    - 输出：完整的 prompt   PromptValue
'''

def format_func(docs: list[Document]):
    if not docs:
        return "无相关参考资料"
    formatted_str = "["
    for doc in docs:
        formatted_str += doc.page_content + "; "
    formatted_str += "]"
    return formatted_str

def print_prompt(prompt):
    logger.info(prompt.to_string())
    logger.info("="*20)
    return prompt

# * 这里在 chain.invoke(input_text) 后实际上 input_text 是传递给了 retriever，因为使用了 RunnablePassthrough，因此也会传递一份给 "input"
# * 得到的结果类似 {"input": "怎么减肥？", "context": "[完整的参考资料]"}
chain = (
    {"input": RunnablePassthrough(), "context": retriever | format_func} | prompt | print_prompt | model | StrOutputParser()
)

# * chain 调用 invoke() 方法，则 chain 中每一个组件都会调用其 invoke() 方法
res = chain.invoke(input_text)
logger.info(res)
