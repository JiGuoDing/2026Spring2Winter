"""
SQLite Checkpointer 示例

演示内容：
1. 使用 SqliteSaver 持久化 State
2. thread_id 的使用
3. 恢复中断的对话
4. 查看检查点历史

运行方式：
python sqlite_checkpointer.py
"""

from typing import TypedDict, Annotated, List
from operator import add
import sqlite3
import os

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver


# ============================================
# 1. 定义 State
# ============================================

class ChatState(TypedDict):
    """聊天 State"""
    messages: Annotated[List[str], add]
    user_id: str
    turn_count: int


# ============================================
# 2. 定义节点
# ============================================

def chatbot(state: ChatState) -> dict:
    """聊天机器人节点"""
    print(f"\n[Chatbot] 收到消息")
    
    # 模拟回复
    last_message = state["messages"][-1] if state["messages"] else ""
    reply = f"回复: 你说的是 '{last_message}'"
    
    return {
        "messages": [reply],
        "turn_count": state["turn_count"] + 1
    }


# ============================================
# 3. 构建带 Checkpointer 的图
# ============================================

def build_graph_with_sqlite():
    """构建带 SQLite 持久化的图"""
    print("\n" + "=" * 60)
    print("构建带 SQLite Checkpointer 的图")
    print("=" * 60)
    
    # 创建 StateGraph
    graph = StateGraph(ChatState)
    
    # 添加节点
    graph.add_node("chatbot", chatbot)
    graph.set_entry_point("chatbot")
    graph.add_edge("chatbot", END)
    
    # 创建 SQLite 连接
    db_path = "chat_history.db"
    print(f"\n数据库路径: {db_path}")
    
    # 创建连接（重要：需要 check_same_thread=False）
    conn = sqlite3.connect(db_path, check_same_thread=False)
    print("✓ 数据库连接成功")
    
    # 创建 Checkpointer
    memory = SqliteSaver(conn)
    print("✓ Checkpointer 创建成功")
    
    # 编译图（传入 checkpointer）
    app = graph.compile(checkpointer=memory)
    print("✓ 图编译成功")
    
    return app, conn


# ============================================
# 4. 使用 Checkpointer
# ============================================

def example_basic_persistence():
    """示例 1: 基础持久化"""
    print("\n" + "=" * 60)
    print("示例 1: 基础持久化")
    print("=" * 60)
    
    # 清理旧数据库
    if os.path.exists("chat_history.db"):
        os.remove("chat_history.db")
    
    # 构建图
    app, conn = build_graph_with_sqlite()
    
    # 配置（必须包含 thread_id）
    config = {
        "configurable": {
            "thread_id": "conversation_001"
        }
    }
    
    print(f"\nThread ID: {config['configurable']['thread_id']}")
    
    # 第一次对话
    print("\n--- 第一次对话 ---")
    input1 = {
        "messages": ["你好！"],
        "user_id": "user_001",
        "turn_count": 0
    }
    
    result1 = app.invoke(input1, config)
    print(f"消息数: {len(result1['messages'])}")
    print(f"轮数: {result1['turn_count']}")
    
    # 第二次对话（使用同一个 thread_id，会恢复状态）
    print("\n--- 第二次对话（同一线程）---")
    input2 = {
        "messages": ["今天天气怎么样？"],
        "user_id": "user_001",
        "turn_count": 0  # 这个值会被忽略，使用保存的状态
    }
    
    result2 = app.invoke(input2, config)
    print(f"消息数: {len(result2['messages'])}")
    print(f"轮数: {result2['turn_count']}")
    
    # 新线程（独立的状态）
    print("\n--- 新线程（独立状态）---")
    config_new = {
        "configurable": {
            "thread_id": "conversation_002"
        }
    }
    
    input3 = {
        "messages": ["你好，我是新用户"],
        "user_id": "user_002",
        "turn_count": 0
    }
    
    result3 = app.invoke(input3, config_new)
    print(f"消息数: {len(result3['messages'])}")
    print(f"轮数: {result3['turn_count']}")
    
    # 关闭连接
    conn.close()
    print("\n✓ 数据库连接已关闭")


# ============================================
# 5. 查看检查点历史
# ============================================

def example_checkpoint_history():
    """示例 2: 查看检查点历史"""
    print("\n" + "=" * 60)
    print("示例 2: 查看检查点历史")
    print("=" * 60)
    
    # 使用之前的数据库
    db_path = "chat_history.db"
    
    if not os.path.exists(db_path):
        print("数据库不存在，先运行示例 1")
        return
    
    conn = sqlite3.connect(db_path, check_same_thread=False)
    memory = SqliteSaver(conn)
    
    # 构建图
    graph = StateGraph(ChatState)
    graph.add_node("chatbot", chatbot)
    graph.set_entry_point("chatbot")
    graph.add_edge("chatbot", END)
    
    app = graph.compile(checkpointer=memory)
    
    config = {
        "configurable": {
            "thread_id": "conversation_001"
        }
    }
    
    # 查看检查点
    print("\n检查点历史:")
    checkpoints = list(memory.list(config))
    
    for i, checkpoint in enumerate(checkpoints, 1):
        print(f"\n检查点 {i}:")
        print(f"  ID: {checkpoint['id']}")
        print(f"  时间: {checkpoint['ts']}")
        print(f"  父ID: {checkpoint.get('parent_id', 'None')}")
    
    conn.close()


# ============================================
# 6. 多轮对话示例
# ============================================

def example_multi_turn_conversation():
    """示例 3: 多轮对话"""
    print("\n" + "=" * 60)
    print("示例 3: 多轮对话（模拟真实聊天）")
    print("=" * 60)
    
    # 清理数据库
    if os.path.exists("chat_history.db"):
        os.remove("chat_history.db")
    
    app, conn = build_graph_with_sqlite()
    
    config = {
        "configurable": {
            "thread_id": "multi_turn_demo"
        }
    }
    
    # 初始状态
    state = {
        "messages": [],
        "user_id": "user_demo",
        "turn_count": 0
    }
    
    # 多轮对话
    user_messages = [
        "你好，我想学习编程",
        "我应该从什么语言开始？",
        "Python 难学吗？",
        "有什么学习资源推荐？"
    ]
    
    print("\n开始多轮对话:")
    print("-" * 60)
    
    for i, msg in enumerate(user_messages, 1):
        print(f"\n用户 (第 {i} 轮): {msg}")
        
        # 添加用户消息
        state["messages"].append(msg)
        
        # 执行
        state = app.invoke(state, config)
        
        # 显示回复
        bot_reply = state["messages"][-1]
        print(f"机器人: {bot_reply}")
        print(f"当前轮数: {state['turn_count']}")
    
    print("-" * 60)
    print(f"\n对话结束，总共 {state['turn_count']} 轮")
    print(f"消息总数: {len(state['messages'])}")
    
    conn.close()


# ============================================
# 7. 最佳实践
# ============================================

def best_practices():
    """最佳实践建议"""
    print("\n" + "=" * 60)
    print("💡 Checkpointer 最佳实践")
    print("=" * 60)
    print("""
1. Thread ID 管理：
   - 为每个会话生成唯一的 thread_id
   - 可以使用 UUID 或会话 ID
   - 示例：f"session_{user_id}_{timestamp}"

2. 数据库管理：
   - 定期清理旧的检查点
   - 使用连接池提高性能
   - 备份数据库文件

3. 错误处理：
   - 捕获数据库连接异常
   - 实现重试机制
   - 提供降级方案

4. 性能优化：
   - 只保存必要的状态
   - 避免在 State 中存储大数据
   - 使用索引加速查询

5. 安全考虑：
   - 加密敏感数据
   - 控制数据库访问权限
   - 定期审计日志
    """)


# ============================================
# 主函数
# ============================================

def main():
    """主函数"""
    print("\n" + "🚀 " * 30)
    print("LangGraph SQLite Checkpointer 示例")
    print("🚀 " * 30)
    
    # 运行示例
    example_basic_persistence()
    example_checkpoint_history()
    example_multi_turn_conversation()
    best_practices()
    
    # 清理
    if os.path.exists("chat_history.db"):
        os.remove("chat_history.db")
        print("\n✓ 已清理测试数据库")
    
    # 总结
    print("\n" + "=" * 60)
    print("📝 总结")
    print("=" * 60)
    print("""
1. Checkpointer 的作用：
   - 保存 State 的中间状态
   - 支持中断和恢复
   - 实现多轮对话记忆

2. 使用步骤：
   - 创建 Checkpointer（SqliteSaver）
   - 编译图时传入 checkpointer
   - invoke 时提供 thread_id

3. 关键概念：
   - thread_id: 唯一标识一个会话
   - 检查点: State 的快照
   - 恢复: 从检查点继续执行

4. 适用场景：
   - 多轮对话系统
   - 需要中断和继续的工作流
   - 会话状态持久化
    """)
    print("=" * 60)


if __name__ == "__main__":
    main()
