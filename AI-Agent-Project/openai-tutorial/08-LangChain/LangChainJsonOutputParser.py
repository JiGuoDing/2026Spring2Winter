from langchain_core.prompts import PromptTemplate
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser

# 创建所需的解析器
str_parser = StrOutputParser()
json_parser = JsonOutputParser()

# 模型创建
model = ChatTongyi(model="qwen3-max")

# 第一个提示词模板
first_prompt = PromptTemplate.from_template(
    "我邻居姓:{lastname}，刚生了{gender}孩，请为孩子起一个名字，并封装为 JSON 格式给我。"
    "要求 key 是 name，value 就是名字，请严格遵守格式要求。"
)

# 第二个提示词模板
second_prompt = PromptTemplate.from_template(
    "姓名: {name}，请帮我解析含义"
)

chain = first_prompt | model | json_parser | second_prompt | model | str_parser
for chunk in chain.stream({"lastname": "张", "gender": "女"}):
    print(chunk, end="", flush=True)

'''
模型输入: PromptValue 或字符串或序列 (BaseMessage, list, tuple, str, dict)
模型输出: AIMessage
提示词模板输入: 要求是字典
提示词模板输出: PromptValue 对象
StrOutputParser: AIMessage 输入、str 输出
JsonOutputParser: AIMessage 输入、dict 输出
'''