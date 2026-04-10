from langchain_core.prompts import PromptTemplate
from langchain_community.llms.tongyi import Tongyi

# PromptTemplate 表示提示词模板，可以构建一个自定义的基础提示词模板，支持变量的注入，最终生成所需要的提示词
# * zero-shot 思想下，可以基于 PromptTemplate 直接完成
prompt_template = PromptTemplate.from_template("我的领居姓{last_name}，刚生了一个{gender}，请你帮忙起个名字，简单回答。")
model = Tongyi(model="qwen-max")

# # 调用 format 方法注入信息
# prompt_text = prompt_template.format(last_name="基", gender="女儿")

# model = Tongyi(model="qwen-max")
# res = model.invoke(input=prompt_text)
# print(res, end="", flush=True)

chain = prompt_template | model
res = chain.invoke(input={"last_name": "基", "gender": "女儿"})
print(res)