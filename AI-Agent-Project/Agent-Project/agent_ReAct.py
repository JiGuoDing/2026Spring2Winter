"""
知识点主题：ReAct（Reason + Act）智能体范式与多步工具推理。

这个文件想说明的是：
当问题无法只靠模型“脑补”完成时，Agent 需要在“思考（Reason）”与“行动（Act）”之间循环，
通过调用工具获取外部事实，再基于观察结果继续推理，直到完成任务。

一、ReAct 的基本闭环
1) Thought（思考）：当前缺什么信息？下一步该做什么？
2) Action（行动）：调用哪个工具？传入什么参数？
3) Observation（观察）：工具返回了什么事实？
4) 再次 Thought：基于新事实继续推理，直到可以回答用户。

二、为什么 BMI 适合 ReAct 演示
BMI 计算公式为：BMI = 体重(kg) / (身高(m)^2)。
该问题需要至少两个外部数据：体重和身高。
因此模型需要按步骤调用两个工具，收集完事实再计算并解释结果。

三、System Prompt 的控制作用
此处通过 system_prompt 显式约束：
1) 必须按 ReAct 流程处理问题。
2) 每轮只允许调用一个工具。
3) 需要向用户解释思考、行动与观察。
这体现了“提示词即策略”的思想：你可以通过提示词改变 Agent 的行为边界。

四、流式输出与调试价值
代码使用 agent.stream(..., stream_mode="values") 获取增量结果，能够实时看到：
1) 当前模型消息内容。
2) 是否触发了工具调用（tool_calls）。
这对教学和调试非常重要，因为 ReAct 的核心在“过程”而不仅是“最终答案”。

五、实践注意事项
1) 让模型暴露全部思考链在生产环境并不总是合适，可能涉及安全与策略泄露。
2) 更推荐对外给出“简化版解释”，完整推理留在内部日志中。
3) 工具描述（description）应清晰、可执行，减少模型误调用概率。

六、能力进阶方向
1) 给工具增加参数校验与异常处理。
2) 在 ReAct 之外结合 Plan-and-Execute，让复杂任务先规划再执行。
3) 将工具结果结构化（JSON）返回，提高后续推理稳定性。
"""

from langchain.agents import create_agent
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.tools import tool
from loguru import logger


@tool(description="获取体重，返回值是整数，单位千克")
def get_weight() -> int:
    return 85

@tool(description="获取身高，返回值是整数，单位厘米")
def get_height() -> int:
    return 180


if __name__ == "__main__":
    agent = create_agent(
        model=ChatTongyi(
            model="qwen3-max"
        ),
        tools=[get_height, get_weight],
        system_prompt="你是严格遵循 ReAct 框架的智能体，必须按照「思考 -> 行动 -> 观察 -> 再思考」"
                      "的流程解决问题，并且每一轮仅能思考并调用 1 个工具，禁止单次调用多个工具。"
                      "要求告知用户你的思考过程以及调用工具的原因，按思考、行动、观察三个层次告知用户。",
    )

    for chunk in agent.stream(
        {"messages": [
            {"role": "user", "content": "计算我的 BMI 值。"}
        ]},
        stream_mode="values"
    ):
        latest_message = chunk["messages"][-1]
        if latest_message.content:
            logger.info(type(latest_message).__name__ + ": " + latest_message.content)

        try:
            if latest_message.tool_calls:
                logger.info(f"工具调用：{ [tc['name'] for tc in latest_message.tool_calls] }")
        except AttributeError as e:
            pass