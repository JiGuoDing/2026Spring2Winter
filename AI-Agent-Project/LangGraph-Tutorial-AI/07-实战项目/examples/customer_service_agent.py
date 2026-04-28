"""
智能客服 Agent 实战

这是一个完整的智能客服 Agent，能够：
1. 回答常见问题（基于知识库）
2. 创建工单
3. 查询订单状态
4. 转人工客服

运行方式：
python customer_service_agent.py
"""

from typing import TypedDict, Annotated, List, Optional
from operator import add
import os
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
# 1. 知识库和数据库（模拟）
# ============================================

class FAQKnowledgeBase:
    """常见问题知识库"""
    
    def __init__(self):
        self.faqs = {
            "退货": "我们支持 7 天无理由退货。请确保商品未使用且包装完整。",
            "退款": "退款将在 3-5 个工作日内原路返回。",
            "物流": "订单发货后，您会收到物流短信。可在订单详情中查看物流信息。",
            "发票": "我们提供电子发票，可在订单详情页下载。",
            "优惠": "新用户注册可享 9 折优惠，使用代码：NEW10"
        }
    
    def search(self, query: str) -> Optional[str]:
        """搜索相关 FAQ"""
        query_lower = query.lower()
        for keyword, answer in self.faqs.items():
            if keyword in query_lower:
                return answer
        return None


class TicketSystem:
    """工单系统（模拟）"""
    
    def __init__(self):
        self.tickets = []
        self.ticket_counter = 0
    
    def create_ticket(self, user_id: str, issue: str, priority: str = "medium") -> str:
        """创建工单"""
        self.ticket_counter += 1
        ticket_id = f"TK{self.ticket_counter:06d}"
        
        ticket = {
            "ticket_id": ticket_id,
            "user_id": user_id,
            "issue": issue,
            "priority": priority,
            "status": "open",
            "created_at": datetime.now().isoformat()
        }
        
        self.tickets.append(ticket)
        return ticket_id


class OrderSystem:
    """订单系统（模拟）"""
    
    def __init__(self):
        self.orders = {
            "ORD001": {"status": "shipped", "product": "iPhone 15", "tracking": "SF1234567890"},
            "ORD002": {"status": "processing", "product": "MacBook Pro", "tracking": None},
            "ORD003": {"status": "delivered", "product": "AirPods", "tracking": "SF0987654321"}
        }
    
    def get_order_status(self, order_id: str) -> Optional[dict]:
        """查询订单状态"""
        return self.orders.get(order_id)


# 全局实例
faq_kb = FAQKnowledgeBase()
ticket_system = TicketSystem()
order_system = OrderSystem()


# ============================================
# 2. 定义工具
# ============================================

@tool
def search_faq(question: str) -> str:
    """
    FAQ 检索工具：从常见问题知识库中搜索答案
    
    Args:
        question: 用户问题
    
    Returns:
        问题的答案
    """
    print(f"\n[FAQ 工具] 搜索: {question}")
    answer = faq_kb.search(question)
    
    if answer:
        print(f"[FAQ 工具] 找到答案")
        return answer
    else:
        print(f"[FAQ 工具] 未找到相关答案")
        return "抱歉，知识库中没有找到相关信息。我将为您创建工单或转人工客服。"


@tool
def create_ticket(user_id: str, issue: str, priority: str = "medium") -> str:
    """
    工单创建工具：为用户创建服务工单
    
    Args:
        user_id: 用户 ID
        issue: 问题描述
        priority: 优先级（low/medium/high）
    
    Returns:
        工单 ID
    """
    print(f"\n[工单工具] 创建工单: {issue}")
    ticket_id = ticket_system.create_ticket(user_id, issue, priority)
    return f"工单已创建，工单号: {ticket_id}。我们将在 24 小时内处理。"


@tool
def query_order(order_id: str) -> str:
    """
    订单查询工具：查询订单状态和物流信息
    
    Args:
        order_id: 订单号
    
    Returns:
        订单信息
    """
    print(f"\n[订单工具] 查询订单: {order_id}")
    order = order_system.get_order_status(order_id)
    
    if order:
        status_map = {
            "processing": "处理中",
            "shipped": "已发货",
            "delivered": "已送达"
        }
        
        status = status_map.get(order["status"], order["status"])
        result = f"订单 {order_id}: {order['product']}\n状态: {status}"
        
        if order.get("tracking"):
            result += f"\n物流单号: {order['tracking']}"
        
        return result
    else:
        return f"未找到订单 {order_id}"


@tool
def transfer_to_human(user_id: str, reason: str) -> str:
    """
    转人工客服工具
    
    Args:
        user_id: 用户 ID
        reason: 转接原因
    
    Returns:
        转接信息
    """
    print(f"\n[人工客服工具] 转接用户 {user_id}")
    return f"正在为您转接人工客服...（原因：{reason}）\n请稍候，客服人员将尽快为您服务。"


# 工具列表
tools = [search_faq, create_ticket, query_order, transfer_to_human]


# ============================================
# 3. 定义 State
# ============================================

class CustomerServiceState(TypedDict):
    """客服 Agent State"""
    messages: Annotated[List, add]
    user_id: str
    ticket_ids: List[str]
    conversation_type: str  # faq, order, complaint, other


# ============================================
# 4. 初始化模型
# ============================================

def get_model():
    """初始化模型"""
    if os.getenv("OPENAI_API_KEY"):
        model = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            temperature=0.7
        )
    elif os.getenv("DASHSCOPE_API_KEY"):
        model = ChatOpenAI(
            model=os.getenv("DASHSCOPE_MODEL", "qwen-turbo"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            temperature=0.7
        )
    else:
        raise ValueError("未配置 API Key")
    
    return model.bind_tools(tools)


# ============================================
# 5. 定义节点
# ============================================

def customer_service_agent(state: CustomerServiceState) -> dict:
    """客服 Agent 节点"""
    print("\n" + "=" * 60)
    print("[客服 Agent] 处理用户请求...")
    print("=" * 60)
    
    model = get_model()
    
    # 系统提示词
    system_prompt = """你是一个专业的电商客服助手。

职责：
1. 回答常见问题（退货、退款、物流、发票等）
2. 查询订单状态
3. 创建工单处理复杂问题
4. 必要时转人工客服

工作原则：
- 优先使用工具回答问题
- 保持礼貌和专业
- 如果无法解决，创建工单或转人工
- 记住用户 ID 和对话历史"""
    
    messages = state["messages"]
    full_messages = [SystemMessage(content=system_prompt)] + messages
    
    response = model.invoke(full_messages)
    
    has_tools = hasattr(response, 'tool_calls') and response.tool_calls
    print(f"[客服 Agent] {'调用工具' if has_tools else '直接回答'}")
    
    return {"messages": [response]}


def should_use_tool(state: CustomerServiceState) -> str:
    """条件函数"""
    messages = state["messages"]
    last_message = messages[-1]
    
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    else:
        return "end"


# ============================================
# 6. 构建图
# ============================================

def build_customer_service_agent():
    """构建客服 Agent"""
    print("\n" + "=" * 60)
    print("构建智能客服 Agent")
    print("=" * 60)
    
    graph = StateGraph(CustomerServiceState)
    
    tool_node = ToolNode(tools)
    
    graph.add_node("agent", customer_service_agent)
    graph.add_node("tools", tool_node)
    
    graph.add_conditional_edges(
        "agent",
        should_use_tool,
        {"tools": "tools", "end": END}
    )
    
    graph.add_edge("tools", "agent")
    graph.set_entry_point("agent")
    
    app = graph.compile()
    print("✓ 智能客服 Agent 构建完成")
    
    return app


# ============================================
# 7. 运行 Agent
# ============================================

def run_customer_service(app, user_id: str, question: str):
    """运行客服 Agent"""
    print("\n" + "=" * 60)
    print(f"用户 {user_id}: {question}")
    print("=" * 60)
    
    initial_state = {
        "messages": [HumanMessage(content=question)],
        "user_id": user_id,
        "ticket_ids": [],
        "conversation_type": "other"
    }
    
    result = app.invoke(initial_state)
    
    # 输出回答
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and not hasattr(msg, 'tool_calls'):
            print(f"\n客服: {msg.content}")
            break


# ============================================
# 主函数
# ============================================

def main():
    """主函数"""
    print("\n" + "🚀 " * 30)
    print("智能客服 Agent 实战")
    print("🚀 " * 30)
    
    app = build_customer_service_agent()
    
    # 测试场景
    test_cases = [
        ("USER001", "我想退货，怎么操作？"),
        ("USER002", "查询订单 ORD001 的状态"),
        ("USER003", "我的问题很复杂，需要人工帮助"),
        ("USER001", "什么时候能收到退款？"),
    ]
    
    for user_id, question in test_cases:
        run_customer_service(app, user_id, question)
        print("\n" + "=" * 60)
    
    # 总结
    print("\n" + "=" * 60)
    print("📝 总结")
    print("=" * 60)
    print("""
智能客服 Agent 特点：
1. 多工具协作（FAQ、工单、订单、人工）
2. 智能路由（自动判断使用哪个工具）
3. 上下文保持（记住用户和对话历史）
4. 降级策略（无法解决时转人工）

实际应用可扩展：
- 接入真实数据库
- 集成 CRM 系统
- 添加语音支持
- 实现多语言
    """)
    print("=" * 60)


if __name__ == "__main__":
    main()
