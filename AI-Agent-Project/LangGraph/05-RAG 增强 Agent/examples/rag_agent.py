"""
RAG Agent 示例

演示内容：
1. 创建简单的文档检索器
2. 将检索器封装为工具
3. 构建 RAG Agent
4. 基于知识库回答问题

运行方式：
python rag_agent.py

注意：此示例使用简化的检索器，实际应用中应使用向量库
"""

from typing import TypedDict, Annotated, List
from operator import add
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

# 加载环境变量
load_dotenv()


# ============================================
# 1. 创建简单的知识库
# ============================================

class SimpleKnowledgeBase:
    """简单的知识库（模拟向量检索）"""
    
    def __init__(self):
        self.documents = [
            {
                "title": "Python 简介",
                "content": "Python 是一种高级编程语言，由 Guido van Rossum 于 1991 年发布。它以代码可读性著称，支持多种编程范式。",
                "keywords": ["python", "编程语言", "简介"]
            },
            {
                "title": "LangGraph 介绍",
                "content": "LangGraph 是 LangChain 团队开发的框架，用于构建有状态的 Agent 应用。它使用图的概念来编排执行流程。",
                "keywords": ["langgraph", "框架", "agent", "介绍"]
            },
            {
                "title": "LangChain 生态系统",
                "content": "LangChain 是一个用于开发 LLM 应用的框架，包含 LangChain Core、LangGraph、LangSmith 等组件。",
                "keywords": ["langchain", "生态系统", "框架"]
            },
            {
                "title": "RAG 检索增强生成",
                "content": "RAG (Retrieval-Augmented Generation) 是一种结合检索和生成的技术，先从知识库中检索相关信息，再让模型生成回答。",
                "keywords": ["rag", "检索", "增强", "生成"]
            },
            {
                "title": "向量数据库",
                "content": "向量数据库用于存储和检索向量数据，常见的有 Chroma、FAISS、Pinecone 等。它们支持相似度搜索。",
                "keywords": ["向量数据库", "chroma", "faiss", "检索"]
            }
        ]
    
    def search(self, query: str, top_k: int = 2) -> List[dict]:
        """
        搜索相关文档（简化版：基于关键词匹配）
        
        Args:
            query: 查询字符串
            top_k: 返回结果数量
        
        Returns:
            相关文档列表
        """
        query_lower = query.lower()
        results = []
        
        for doc in self.documents:
            # 计算相关性分数
            score = 0
            # 标题匹配
            if any(keyword in query_lower for keyword in doc["title"].lower()):
                score += 3
            # 关键词匹配
            score += sum(1 for keyword in doc["keywords"] if keyword in query_lower)
            # 内容匹配
            if any(keyword in query_lower for keyword in doc["content"].lower()[:50]):
                score += 1
            
            if score > 0:
                results.append((score, doc))
        
        # 按分数排序
        results.sort(key=lambda x: x[0], reverse=True)
        
        # 返回 top_k
        return [doc for _, doc in results[:top_k]]


# 全局知识库实例
knowledge_base = SimpleKnowledgeBase()


# ============================================
# 2. 定义检索工具
# ============================================

@tool
def search_knowledge_base(query: str) -> str:
    """
    知识库检索工具：从知识库中搜索相关信息
    
    Args:
        query: 搜索查询
    
    Returns:
        检索到的文档内容
    """
    print(f"\n[检索工具] 搜索: {query}")
    
    # 搜索文档
    docs = knowledge_base.search(query, top_k=2)
    
    if not docs:
        return "未找到相关文档"
    
    # 格式化结果
    results = []
    for i, doc in enumerate(docs, 1):
        result = f"文档 {i}: {doc['title']}\n{doc['content']}"
        results.append(result)
        print(f"[检索工具] 找到: {doc['title']}")
    
    return "\n\n".join(results)


# 工具列表
tools = [search_knowledge_base]


# ============================================
# 3. 定义 State
# ============================================

class RAGState(TypedDict):
    """RAG Agent State"""
    messages: Annotated[List, add]
    retrieved_docs: List[str]
    query_count: int


# ============================================
# 4. 初始化模型
# ============================================

def get_model():
    """初始化聊天模型"""
    if os.getenv("OPENAI_API_KEY"):
        model = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            temperature=0.7
        )
        print("✓ 使用 OpenAI 模型")
    elif os.getenv("DASHSCOPE_API_KEY"):
        model = ChatOpenAI(
            model=os.getenv("DASHSCOPE_MODEL", "qwen-turbo"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            temperature=0.7
        )
        print("✓ 使用通义千问模型")
    else:
        raise ValueError("未配置 API Key")
    
    # 绑定工具
    model_with_tools = model.bind_tools(tools)
    return model_with_tools


# ============================================
# 5. 定义节点
# ============================================

def rag_agent_node(state: RAGState) -> dict:
    """RAG Agent 节点"""
    print("\n" + "=" * 60)
    print("[RAG Agent] 思考中...")
    print("=" * 60)
    
    model = get_model()
    
    # 构建系统提示词
    system_prompt = """你是一个知识助手，专门基于知识库回答问题。
工作流程：
1. 如果用户问题需要查询知识库，调用 search_knowledge_base 工具
2. 基于检索到的文档生成回答
3. 如果知识库没有相关信息，告知用户

要求：
- 回答要基于检索到的内容
- 注明信息来源
- 保持准确和简洁"""
    
    # 获取消息
    messages = state["messages"]
    
    # 添加系统提示词
    full_messages = [SystemMessage(content=system_prompt)] + messages
    
    # 调用模型
    response = model.invoke(full_messages)
    
    # 检查是否有工具调用
    has_tools = hasattr(response, 'tool_calls') and response.tool_calls
    print(f"[RAG Agent] {'需要检索' if has_tools else '直接回答'}")
    
    return {
        "messages": [response],
        "query_count": state.get("query_count", 0) + (1 if has_tools else 0)
    }


def should_retrieve(state: RAGState) -> str:
    """条件函数：是否需要检索"""
    messages = state["messages"]
    last_message = messages[-1]
    
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    else:
        return "end"


# ============================================
# 6. 构建图
# ============================================

def build_rag_agent():
    """构建 RAG Agent"""
    print("\n" + "=" * 60)
    print("构建 RAG Agent")
    print("=" * 60)
    
    graph = StateGraph(RAGState)
    
    # 创建工具节点
    tool_node = ToolNode(tools)
    
    # 添加节点
    graph.add_node("agent", rag_agent_node)
    graph.add_node("tools", tool_node)
    
    # 添加条件边
    graph.add_conditional_edges(
        "agent",
        should_retrieve,
        {"tools": "tools", "end": END}
    )
    
    # 添加工具返回边
    graph.add_edge("tools", "agent")
    
    # 设置入口
    graph.set_entry_point("agent")
    
    # 编译
    app = graph.compile()
    print("✓ RAG Agent 构建完成")
    
    return app


# ============================================
# 7. 运行 RAG Agent
# ============================================

def run_rag_agent(app, question: str):
    """运行 RAG Agent"""
    print("\n" + "=" * 60)
    print(f"问题: {question}")
    print("=" * 60)
    
    # 初始 State
    initial_state = {
        "messages": [HumanMessage(content=question)],
        "retrieved_docs": [],
        "query_count": 0
    }
    
    # 执行
    print("\n开始执行...")
    print("-" * 60)
    result = app.invoke(initial_state)
    print("-" * 60)
    
    # 输出结果
    print("\n" + "=" * 60)
    print("回答")
    print("=" * 60)
    
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and not hasattr(msg, 'tool_calls'):
            print(f"\n{msg.content}")
            break
    
    print(f"\n检索次数: {result['query_count']}")


# ============================================
# 主函数
# ============================================

def main():
    """主函数"""
    print("\n" + "🚀 " * 30)
    print("LangGraph RAG Agent 示例")
    print("🚀 " * 30)
    
    # 构建 Agent
    app = build_rag_agent()
    
    # 测试问题
    questions = [
        "Python 是什么？",
        "LangGraph 有什么用？",
        "什么是 RAG？",
        "有哪些向量数据库？"
    ]
    
    # 运行测试
    for question in questions:
        run_rag_agent(app, question)
        print("\n" + "=" * 60)
    
    # 总结
    print("\n" + "=" * 60)
    print("📝 总结")
    print("=" * 60)
    print("""
1. RAG Agent 的工作流程：
   用户问题 → Agent 判断 → 检索知识库 → 基于文档生成回答

2. 关键组件：
   - 知识库：存储文档和向量
   - 检索工具：封装检索逻辑
   - Agent 节点：决定何时检索
   - 提示词：指导模型使用检索结果

3. 实际应用：
   - 使用真实的向量库（Chroma/FAISS）
   - 实现文档切片和向量化
   - 优化检索策略
   - 添加引用来源
    """)
    print("=" * 60)


if __name__ == "__main__":
    main()
