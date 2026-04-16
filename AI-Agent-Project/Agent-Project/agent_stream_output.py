"""
知识点主题：Agent 的流式输出（Streaming）与工具调用过程可视化。

这个文件主要讲“如何观察 Agent 正在做什么”，而不是只等待最终结果。
在真实场景中，用户往往更在意系统是否“在工作中”，以及中间步骤是否可靠。

一、为什么需要流式输出
1) 交互体验更好：长任务不再“卡住无响应”，用户能持续看到进度。
2) 调试效率更高：可以定位到底是模型生成慢，还是工具调用慢。
3) 过程透明：可追踪 Agent 在何时决定调用哪个工具。

二、此文件演示的关键能力
1) 使用 agent.stream(...) 获取增量消息块 chunk。
2) 从 chunk 中提取 latest_message，实时打印当前输出文本。
3) 检查 latest_message.tool_calls，展示本轮触发了哪些工具。

三、工具设计与职责分离
这里定义了两个工具：
1) get_price：专注“价格查询”事实。
2) get_info：专注“公司介绍”事实。
这种拆分有助于模型精准调用，也有利于后续替换真实数据源（行情 API、企业数据库）。

四、系统提示词与行为引导
system_prompt 要求解释思考过程并说明调用工具理由。
这会显著提升输出的可解释性，让用户知道答案不是“拍脑袋”，而是有依据的。

五、工程化建议
1) 对每个 chunk 打上时间戳，统计端到端延迟与各阶段耗时。
2) 对工具调用结果做结构化记录，方便后续做质量评估与回放。
3) 当出现 tool_calls 但工具失败时，应向用户反馈“已识别问题并重试/降级”。

六、学习价值
掌握 Streaming 后，你会从“离线问答”迈向“在线交互式 Agent”。
这在客服、投研分析、代码助手等实时场景中非常重要。
"""

from langchain.agents import create_agent
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.tools import tool
from loguru import logger


@tool(description="获取股票价格，传入股票名称，返回字符串信息")
def get_price(name: str) -> str:
    return f"股票 {name} 的价格为 20。"


@tool(description="获取股票信息，传入股票名称，返回字符串信息")
def get_info(name: str) -> str:
    return f"股票 {name} 是一家 A 股上市公司，专注于 IT 职业教育。"


if __name__ == "__main__":
    agent = create_agent(
        model=ChatTongyi(
            model="qwen3-max"
        ),
        tools=[get_price, get_info],
        system_prompt="你是一个智能助手，可以回答与股票相关的问题，要求告知用户你的思考过程，并且说明调用某个工具的理由。",
    )

    for chunk in agent.stream(
        {"messages": [
            {"role": "user", "content": "传智教育的股价是多少，并介绍一下这家公司。"}
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