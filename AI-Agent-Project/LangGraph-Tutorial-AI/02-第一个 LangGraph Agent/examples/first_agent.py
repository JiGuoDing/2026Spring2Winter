"""
第一个完整 LangGraph Agent 示例

这是一个完整的 ReAct Agent，能够：
1. 接收用户问题
2. 决定是否需要调用工具
3. 执行工具调用
4. 基于工具结果生成回答

工具包括：
- 计算器：执行数学计算
- 天气查询：查询城市天气（模拟）
- 时间查询：获取当前时间

运行方式：
python first_agent.py

注意：需要配置 OPENAI_API_KEY 或 DASHSCOPE_API_KEY
"""

import os
from typing import TypedDict, Annotated, List
from operator import add
from datetime import datetime

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

# 加载环境变量
load_dotenv()


# ============================================
# 1. 定义工具
# ============================================

@tool
def calculator(expression: str) -> str:
    """
    计算器工具：执行数学表达式计算
    
    Args:
        expression: 数学表达式，如 "2 + 2", "10 * 5", "100 / 3"
    
    Returns:
        计算结果
    """
    try:
        # 安全评估数学表达式
        result = eval(expression, {"__builtins__": {}}, {})
        return f"{expression} = {result}"
    except Exception as e:
        return f"计算错误: {str(e)}"


@tool
def get_weather(city: str) -> str:
    """
    天气查询工具：查询指定城市的天气（模拟）
    
    Args:
        city: 城市名称，如 "北京", "上海", "广州"
    
    Returns:
        天气信息
    """
    # 模拟天气数据
    weather_data = {
        "北京": "晴天，温度 20-25°C，空气质量 良",
        "上海": "多云，温度 22-27°C，空气质量 优",
        "广州": "阴天，温度 25-30°C，空气质量 中等",
        "深圳": "晴天，温度 26-31°C，空气质量 优",
        "杭州": "小雨，温度 18-23°C，空气质量 良",
    }
    
    weather = weather_data.get(city, f"暂无 {city} 的天气数据")
    return f"{city} 天气: {weather}"


@tool
def get_current_time() -> str:
    """
    时间查询工具：获取当前时间
    
    Returns:
        当前时间字符串
    """
    now = datetime.now()
    return f"当前时间: {now.strftime('%Y年%m月%d日 %H:%M:%S')}"


# 工具列表
tools = [calculator, get_weather, get_current_time]


# ============================================
# 2. 定义 State
# ============================================

class AgentState(TypedDict):
    """Agent 的状态"""
    # 消息历史（使用 add reducer 追加消息）
    messages: Annotated[List, add]
    
    # 工具调用次数
    tool_call_count: int


# ============================================
# 3. 初始化模型
# ============================================

def get_model():
    """
    初始化聊天模型
    
    Returns:
        绑定了工具的聊天模型
    """
    # 检查 API Key
    if os.getenv("OPENAI_API_KEY"):
        # 使用 OpenAI
        model = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            temperature=0.7
        )
        print("✓ 使用 OpenAI 模型")
    elif os.getenv("DASHSCOPE_API_KEY"):
        # 使用通义千问
        model = ChatOpenAI(
            model=os.getenv("DASHSCOPE_MODEL", "qwen-turbo"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            temperature=0.7
        )
        print("✓ 使用通义千问模型")
    else:
        raise ValueError("未配置 API Key，请设置 OPENAI_API_KEY 或 DASHSCOPE_API_KEY")
    
    # 绑定工具到模型
    model_with_tools = model.bind_tools(tools)
    print(f"✓ 已绑定 {len(tools)} 个工具")
    
    return model_with_tools


# ============================================
# 4. 定义节点
# ============================================

def agent_node(state: AgentState) -> dict:
    """
    Agent 节点：决定是调用工具还是直接回答
    
    Args:
        state: 当前状态
    
    Returns:
        状态更新（新消息）
    """
    print("\n" + "=" * 60)
    print("[Agent 节点] 开始思考...")
    print("=" * 60)
    
    # 获取模型
    model = get_model()
    
    # 获取消息历史
    messages = state["messages"]
    
    # 调用模型
    print(f"\n[Agent 节点] 发送 {len(messages)} 条消息给模型...")
    response = model.invoke(messages)
    
    print(f"[Agent 节点] 模型响应类型: {type(response).__name__}")
    
    # 检查是否有工具调用
    if hasattr(response, 'tool_calls') and response.tool_calls:
        print(f"[Agent 节点] 模型决定调用 {len(response.tool_calls)} 个工具")
        for tc in response.tool_calls:
            print(f"  - 工具: {tc['name']}, 参数: {tc['args']}")
    else:
        print(f"[Agent 节点] 模型直接回答")
    
    # 返回更新
    return {
        "messages": [response],
        "tool_call_count": state.get("tool_call_count", 0) + (1 if hasattr(response, 'tool_calls') and response.tool_calls else 0)
    }


def should_call_tools(state: AgentState) -> str:
    """
    条件函数：判断是否需要调用工具
    
    Args:
        state: 当前状态
    
    Returns:
        "tools" 或 "end"
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    # 检查最后一条消息是否有工具调用
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        print("\n[条件判断] → 需要调用工具")
        return "tools"
    else:
        print("\n[条件判断] → 不需要调用工具，结束")
        return "end"


# ============================================
# 5. 构建图
# ============================================

def build_agent_graph():
    """
    构建 Agent 图
    
    流程：
    用户输入 → Agent 节点 → [是否有工具调用？]
                                 ↓
                        ┌────────┴────────┐
                        ↓                 ↓
                     Tools 节点         END
                        ↓
                    Agent 节点（继续）
    """
    print("\n" + "=" * 60)
    print("构建 Agent 图")
    print("=" * 60)
    
    # 创建 StateGraph
    graph = StateGraph(AgentState)
    print("\n✓ 创建 StateGraph")
    
    # 创建工具节点（LangGraph 提供的预建节点）
    tool_node = ToolNode(tools)
    
    # 添加节点
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    print("✓ 添加节点: agent, tools")
    
    # 添加条件边（Agent 节点决定下一步）
    graph.add_conditional_edges(
        "agent",
        should_call_tools,
        {
            "tools": "tools",  # 调用工具
            "end": END         # 结束
        }
    )
    print("✓ 添加条件边: agent → [tools/end]")
    
    # 添加普通边（工具执行后返回 Agent）
    graph.add_edge("tools", "agent")
    print("✓ 添加普通边: tools → agent")
    
    # 设置入口节点
    graph.set_entry_point("agent")
    print("✓ 设置入口节点: agent")
    
    # 编译图
    app = graph.compile()
    print("✓ 编译图完成")
    
    return app


# ============================================
# 6. 运行 Agent
# ============================================

def run_agent(app, user_input: str):
    """
    运行 Agent
    
    Args:
        app: 编译后的图
        user_input: 用户输入
    """
    print("\n" + "=" * 60)
    print(f"用户输入: {user_input}")
    print("=" * 60)
    
    # 初始 State
    initial_state = {
        "messages": [
            SystemMessage(content="你是一个有帮助的助手。如果需要使用工具，请调用它们。"),
            HumanMessage(content=user_input)
        ],
        "tool_call_count": 0
    }
    
    # 执行
    print("\n开始执行 Agent...")
    print("-" * 60)
    result = app.invoke(initial_state)
    print("-" * 60)
    
    # 输出结果
    print("\n" + "=" * 60)
    print("Agent 回答")
    print("=" * 60)
    
    # 获取最后一条 AI 消息
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and not hasattr(msg, 'tool_calls'):
            print(f"\n{msg.content}")
            break
    
    print(f"\n工具调用次数: {result['tool_call_count']}")
    print(f"总消息数: {len(result['messages'])}")


# ============================================
# 主函数
# ============================================

def main():
    """主函数"""
    print("\n" + "🚀 " * 30)
    print("第一个完整 LangGraph Agent")
    print("🚀 " * 30)
    
    # 构建 Agent 图
    app = build_agent_graph()
    
    # 测试场景 1：需要调用计算器
    run_agent(app, "计算 123 * 456 等于多少？")
    
    # 测试场景 2：需要查询天气
    run_agent(app, "北京今天天气怎么样？")
    
    # 测试场景 3：需要查询时间
    run_agent(app, "现在几点了？")
    
    # 测试场景 4：不需要工具
    run_agent(app, "你好，请介绍一下自己")
    
    # 总结
    print("\n" + "=" * 60)
    print("📝 总结")
    print("=" * 60)
    print("""
1. Agent 的核心组件：
   - State：管理消息历史和状态
   - Agent 节点：调用模型决定下一步
   - Tools 节点：执行工具调用
   - 条件边：根据模型输出选择流程

2. 工作流程：
   用户输入 → Agent 思考 → 决定调用工具 → 执行工具 → Agent 基于结果回答

3. 工具定义：
   - 使用 @tool 装饰器
   - 提供清晰的描述（影响模型选择）
   - 类型注解参数

4. 关键点：
   - 模型必须绑定工具（bind_tools）
   - 使用 ToolNode 自动执行工具
   - 条件边检查是否有 tool_calls

5. 扩展方向：
   - 添加更多工具
   - 实现对话历史管理
   - 添加记忆系统
   - 集成 RAG 检索
    """)
    print("=" * 60)


if __name__ == "__main__":
    main()
