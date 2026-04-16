"""
知识点主题：Agent 入门最小闭环（模型 + 工具 + 消息协议 + 一次调用）。

这个文件是最核心的入门样例，目标是帮助你建立 Agent 的“最小可运行心智模型”：
只要具备一个模型、一个工具、一次消息输入，就能完成一次可解释的任务执行。

一、最小闭环由哪些部分组成
1) 模型（model）：负责自然语言理解、规划与回复生成。
2) 工具（tools）：负责访问外部能力或确定性计算（如天气、数据库、搜索）。
3) 系统提示词（system_prompt）：定义 Agent 的角色和行为边界。
4) 消息输入（messages）：用户问题通过统一协议传入。
5) 调用方式（invoke）：执行一次完整推理并返回结果。

二、为什么工具函数要用 @tool 装饰器
@tool 会把普通函数注册为“可被模型识别和调用”的工具。
函数签名与描述信息（description）会成为模型决策依据。
描述写得越清晰，模型越容易选对工具。

三、消息协议的重要性
该文件使用 {"role": "user", "content": "..."} 的消息结构。
这是 Agent 框架中的通用输入形态，便于多轮对话、上下文拼接与审计回放。

四、invoke 与 stream 的区别
1) invoke：一次性返回完整结果，适合短任务、批处理。
2) stream：边生成边返回，适合实时交互和过程展示。
本文件选 invoke，是为了突出“最小闭环”而非“过程可视化”。

五、从 Demo 到真实项目
1) 将 get_weather 替换为真实天气 API。
2) 给工具增加异常处理和超时控制。
3) 在返回消息中加入来源说明（如数据时间、数据源名称）。
4) 增加日志与监控，提升可维护性。

六、学习建议
先吃透这个最小样例，再逐步学习 ReAct、Streaming、Middleware。
这样可以避免一开始就陷入复杂框架细节，学习路径更稳。
"""

from langchain.agents import create_agent
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.tools import tool
from loguru import logger


@tool(description="查询天气")
def get_weather() -> str:
    return "晴天"

agent = create_agent(
    # Agent 的大脑 LLM
    model=ChatTongyi(
        model="qwen3-max"
    ),
    # 向智能体提供工具列表
    tools=[get_weather],
    system_prompt="你是一个聊天助手，可以回答用户的问题"
)
res = agent.invoke(
    input={
        "messages": [
            {"role": "user", "content": "明天南京的天气如何？"}
        ]
    }
)

for msg in res["messages"]:
    logger.info(type(msg).__name__ + ": " + msg.content)