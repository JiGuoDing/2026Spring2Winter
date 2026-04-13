from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_community.chat_models.tongyi import ChatTongyi

# * 将 model 输出的 AIMessage 转换为 <class 'langchain_core.messages.base.TextAccessor'> (是 str 的子类)
# * 同样是 Runnable 的子类，可以加入到链中
parser = StrOutputParser()

model = ChatTongyi(model="qwen3-max")

prompt = PromptTemplate.from_template(
    "我邻居姓:{lastname}，刚生了{gender}孩，请为孩子起一个名字，仅需要告知我名字而无需其他内容。"
)

chain = prompt | model | parser | model | parser

res = chain.invoke({"lastname": "张", "gender": "女"}) 
for chunk in res:
    print(chunk, end="", flush=True)
print(type(res))
