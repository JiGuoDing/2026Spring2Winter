from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate
from langchain_community.llms.tongyi import Tongyi

# 示例的模板
example_template = PromptTemplate.from_template("单词：{word}，反义词：{antonym}")
# 示例的动态数据注入，要求 list 内部套字典
examples_data = [
    {"word": "热", "antonym": "冷"},
    {"word": "高", "antonym": "矮"},
    {"word": "快", "antonym": "慢"},
    {"word": "大", "antonym": "小"},
    {"word": "上", "antonym": "下"},
]

few_shot_template = FewShotPromptTemplate(
    example_prompt=example_template,      # 示例数据的模板
    examples=examples_data,      # 示例的数据（用来注入动态数据的），list 内套字典
    prefix="告诉我单词的反义词，我提供如下的示例：",        # 示例之前的提示词
    suffix="基于前面的示例告诉我，{input_word}的反义词是？",        # 示例之后的提示词
    input_variables=["input_word"]  # 声明在前缀或后缀中所需要注入的变量名
)

prompt_text = few_shot_template.invoke(input={"input_word": "强"}).to_string()
print(prompt_text)

# * 创建模型
model = Tongyi(model="qwen-max")
resp = model.invoke(input=prompt_text)

print(resp, end="", flush=True)