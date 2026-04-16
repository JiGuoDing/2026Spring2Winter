"""
知识点主题：LangChain Agent Middleware（中间件）与 Agent 全生命周期可观测性。

这个文件重点演示了一个非常关键但常被初学者忽略的能力：
不仅要让 Agent 能“回答问题”，还要让它的执行过程“可观测、可追踪、可审计、可插桩”。

一、为什么需要 Middleware
1) 在生产环境里，Agent 往往会调用模型和工具多次，链路较长，问题排查困难。
2) 仅看最终回答通常不够，需要知道：什么时候调用了模型、调用了哪些工具、参数是什么、返回了什么。
3) Middleware 提供了统一拦截点，可以做日志、监控、权限校验、限流、重试、告警、成本统计等。

二、这个文件覆盖的六类拦截时机
1) before_agent：Agent 启动前触发，适合记录会话入口信息。
2) after_agent：Agent 结束后触发，适合记录会话出口信息与整体耗时。
3) before_model：模型调用前触发，适合做输入检查、提示词注入、Token 预算预估。
4) after_model：模型调用后触发，适合做输出质量检查、格式验证、审计。
5) wrap_model_call：包裹模型调用过程，可拿到请求与响应，适合做统一埋点、异常处理、兜底逻辑。
6) wrap_tool_call：包裹工具调用过程，可读取工具名与参数，适合做工具权限控制、参数脱敏、调用统计。

三、装饰器思想与 AOP（面向切面）
这里用装饰器声明中间件函数，本质是把“横切关注点”（日志、监控、鉴权）
从“业务逻辑”（回答天气）里分离出去。这样代码具备更好的可维护性：
1) 主流程更干净。
2) 横切逻辑可复用。
3) 改动审计策略不需要改业务代码。

四、工程实践建议
1) 日志中避免直接打印敏感信息，必要时进行脱敏（如手机号、证件号、密钥）。
2) 为每次请求分配 trace_id，串联模型调用和工具调用，方便排错。
3) 对工具调用增加超时与重试策略，降低外部依赖不稳定带来的影响。
4) 在 after_model 阶段可加入内容安全检查，防止不合规输出。

五、学习价值
学会 Middleware 后，你会从“能跑 Demo”进阶到“可运维、可治理”的 Agent 系统设计。
这也是从个人实验走向团队协作和生产部署的关键一步。
"""

from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import before_agent, after_agent, before_model, after_model, wrap_model_call, \
    wrap_tool_call
from langchain_community.chat_models.tongyi import ChatTongyi
from langgraph.runtime import  Runtime
from langchain_core.tools import tool
from loguru import logger


@tool(description="查询天气，传入城市名称，返回城市天气信息")
def get_weather(city: str) -> str:
    return f"{city} 的天气为晴天"

"""
1. agent 执行前
2. agent 执行后
3. model 执行前
4. model 执行后
5. 工具执行中
6. 模型执行中
"""

@before_agent
def log_before_agent(state: AgentState, runtime: Runtime):
    logger.info(f"[before_agent] agent 启动，附带 {len(state['messages'])} 条消息")

@after_agent
def log_after_agent(state: AgentState, runtime: Runtime):
    logger.info(f"[after_agent] agent 关闭，附带 {len(state['messages'])} 条消息")

@before_model
def log_before_model(state: AgentState, runtime: Runtime):
    logger.info(f"[before_model] model 即将调用，附带 {len(state['messages'])} 条消息")

@after_model
def log_after_model(state: AgentState, runtime: Runtime):
    logger.info(f"[after_model] model 调用结束，附带 {len(state['messages'])} 条消息")

@wrap_model_call
def model_call_hook(request, handler):
    logger.info(f"[wrap_model_call] 模型调用中，输入参数 {request}")
    response = handler(request)
    logger.info(f"[wrap_model_call] 模型调用结束，输出结果 {response}")
    return response

@wrap_tool_call
def monitor_tool(request, handler):
    logger.info(f"[wrap_tool_call] 工具执行 {request.tool_call['name']}")
    logger.info(f"[wrap_tool_call] 工具执行传入参数：{request.tool_call['args']}")
    return handler(request)

if __name__ == "__main__":
    agent = create_agent(
        model=ChatTongyi(
            model="qwen3-max"
        ),
        tools=[get_weather],
        middleware=[log_after_agent, log_before_agent, log_before_model, log_after_model, model_call_hook, monitor_tool],
    )

    res = agent.invoke({
        "messages": [
            {"role": "user", "content": "今天南京的天气如何？我应该如何选择衣服？"}
        ]
    })

    logger.info(res)