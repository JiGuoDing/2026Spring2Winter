from langchain_core.prompts import PromptTemplate, FewShotPromptTemplate, ChatPromptTemplate

'''
PromptTemplate -> StringPromptTemplate -> BasePromptTemplate (包含 format 方法) -> RunnableSerializable -> Runnable (包含 invoke 方法)
FewShotPromptTemplate -> StringPromptTemplate -> BasePromptTemplate -> RunnableSerializable -> Runnable
ChatPromptTemplate StringPromptTemplate -> BasePromptTemplate -> RunnableSerializable -> Runnable
'''

template = PromptTemplate.from_template("名字是：{name}，爱好是：{hobby}")

res1 = template.format(name="张三", hobby="篮球")
res2 = template.invoke({"name": "张三", "hobby": "篮球"})

print(res1, type(res1))
print(res2, type(res2))