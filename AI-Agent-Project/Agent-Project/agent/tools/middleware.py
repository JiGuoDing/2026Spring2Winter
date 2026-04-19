from typing import Callable

from langchain.agents import AgentState
from langchain.agents.middleware import wrap_tool_call, before_model, dynamic_prompt, ModelRequest
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.runtime import Runtime
from langgraph.types import Command

from utils.logger_handler import logger
from utils.prompt_loader import load_system_prompts, load_report_prompts


@wrap_tool_call
def monitor_tool(
        # 请求的数据封装
        request: ToolCallRequest,
        # 执行的函数本身
        handler: Callable[[ToolCallRequest], ToolMessage | Command]
) -> ToolMessage | Command:
    """
    监控工具的执行
    :param request:
    :param handler:
    :return:
    """

    logger.info(f"[INFO] - [tool monitor] 执行工具: {request.tool_call['name']}")
    logger.info(f"[INFO] - [tool monitor] 传入参数: {request.tool_call['args']}")

    try:
        result = handler(request)
        logger.info(f"[INFO] - [tool monitor] 工具 {request.tool_call['name']} 调用成功")

        if request.tool_call["name"] == "fill_context_for_report":
            # 一旦模型调用工具 fill_context_for_report，就触发标记
            request.runtime.context["report"] = True
        return result
    except Exception as e:
        logger.error(f"工具 {request.tool_call['name']} 调用失败，原因: {str(e)}")
        raise e

@before_model
def log_before_model(
        # 整个 Agent 中的状态记录
        state: AgentState,
        # 记录了整个执行过程中的上下文信息
        runtime: Runtime,
):
    logger.info(f"[INFO] - [log_before_model] 即将调用模型，带有 {len(state['messages'])} 条消息。")
    logger.debug(f"[DEBUG] - [log_before_model] {type(state['messages'][-1]).__name__} {state['messages'][-1].content.strip()}")

    return None

# * 每一次在生成提示词之前，调用此函数
@dynamic_prompt
def report_prompt_switch(request: ModelRequest):
    # 判断是否是报告场景
    report_enabled = request.runtime.context.get("report", False)
    if report_enabled:
        # 确认是当前生成的提示词是服务于报告场景，返回报告生成提示词内容
        return load_report_prompts()
    return load_system_prompts()
