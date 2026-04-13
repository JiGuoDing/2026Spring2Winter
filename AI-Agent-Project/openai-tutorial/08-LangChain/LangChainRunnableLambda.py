from langchain_core.runnables import RunnableLambda
from langchain_core.prompts import PromptTemplate
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.output_parsers import StrOutputParser

model = ChatTongyi(model="qwen3-max")
str_parser = StrOutputParser()

# 第一个提示词模板
first_prompt = PromptTemplate.from_template(
    "我邻居姓:{lastname}，刚生了{gender}孩，请为孩子起一个名字，仅告知我名字，无需额外信息。"
)

# 第二个提示词模板
second_prompt = PromptTemplate.from_template(
    "姓名: {name}，请帮我解析含义"
)

# * 函数的入参：AIMessage -> dict
# 即组装出一个字典
my_func = RunnableLambda(lambda ai_msg: {"name": ai_msg.content})

# chain = first_prompt | model | my_func | second_prompt | model | str_parser
# 既可使用 RunnableLambda 也可使用 lambda 表达式，执行时会自动转换为 RunnableLambda 类
chain = first_prompt | model | (lambda ai_msg: {"name": ai_msg.content}) | second_prompt | model | str_parser

for chunk in chain.stream({"lastname": "王", "gender": "女"}):
    print(chunk, end="", flush=True)