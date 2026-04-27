"""
简单节点图示例

演示内容：
1. 定义 State
2. 创建节点函数
3. 构建 StateGraph
4. 添加节点和边
5. 编译和执行图

运行方式：
python simple_node.py
"""

from typing import TypedDict
from langgraph.graph import StateGraph, END


# ============================================
# 1. 定义 State
# ============================================

class SimpleState(TypedDict):
    """简单的 State 定义"""
    message: str      # 当前消息
    step_count: int   # 步骤计数


# ============================================
# 2. 定义节点函数
# ============================================

def node_1(state: SimpleState) -> dict:
    """
    节点 1：处理消息
    
    Args:
        state: 当前状态
    
    Returns:
        State 的更新（只返回需要更新的字段）
    """
    print(f"\n[节点 1] 输入: {state['message']}")
    
    # 处理逻辑
    new_message = state["message"] + " → 经过节点 1 处理"
    new_count = state["step_count"] + 1
    
    print(f"[节点 1] 输出: {new_message}")
    
    # 返回 State 更新
    return {
        "message": new_message,
        "step_count": new_count
    }


def node_2(state: SimpleState) -> dict:
    """
    节点 2：进一步处理消息
    
    Args:
        state: 当前状态
    
    Returns:
        State 的更新
    """
    print(f"\n[节点 2] 输入: {state['message']}")
    
    # 处理逻辑
    new_message = state["message"] + " → 经过节点 2 处理"
    new_count = state["step_count"] + 1
    
    print(f"[节点 2] 输出: {new_message}")
    
    # 返回 State 更新
    return {
        "message": new_message,
        "step_count": new_count
    }


def node_3(state: SimpleState) -> dict:
    """
    节点 3：最终处理
    
    Args:
        state: 当前状态
    
    Returns:
        State 的更新
    """
    print(f"\n[节点 3] 输入: {state['message']}")
    
    # 处理逻辑
    new_message = state["message"] + " → 经过节点 3 处理（完成）"
    new_count = state["step_count"] + 1
    
    print(f"[节点 3] 输出: {new_message}")
    
    # 返回 State 更新
    return {
        "message": new_message,
        "step_count": new_count
    }


# ============================================
# 3. 构建图
# ============================================

def build_graph():
    """
    构建 StateGraph
    
    流程：node_1 → node_2 → node_3 → END
    """
    print("\n" + "=" * 60)
    print("构建 StateGraph")
    print("=" * 60)
    
    # 创建 StateGraph 实例
    graph = StateGraph(SimpleState)
    print("\n✓ 创建 StateGraph")
    
    # 添加节点
    graph.add_node("node_1", node_1)
    graph.add_node("node_2", node_2)
    graph.add_node("node_3", node_3)
    print("✓ 添加节点: node_1, node_2, node_3")
    
    # 添加边（定义流转关系）
    graph.add_edge("node_1", "node_2")  # node_1 完成后执行 node_2
    graph.add_edge("node_2", "node_3")  # node_2 完成后执行 node_3
    graph.add_edge("node_3", END)       # node_3 完成后结束
    print("✓ 添加边: node_1 → node_2 → node_3 → END")
    
    # 设置入口节点
    graph.set_entry_point("node_1")
    print("✓ 设置入口节点: node_1")
    
    # 编译图
    app = graph.compile()
    print("✓ 编译图完成")
    
    return app


# ============================================
# 4. 执行图
# ============================================

def run_graph(app, initial_message: str):
    """
    执行图
    
    Args:
        app: 编译后的图
        initial_message: 初始消息
    """
    print("\n" + "=" * 60)
    print("执行图")
    print("=" * 60)
    
    # 准备初始 State
    initial_state = {
        "message": initial_message,
        "step_count": 0
    }
    print(f"\n初始 State:")
    print(f"  message: {initial_state['message']}")
    print(f"  step_count: {initial_state['step_count']}")
    
    # 执行图
    print("\n开始执行...")
    print("-" * 60)
    result = app.invoke(initial_state)
    print("-" * 60)
    
    # 输出结果
    print("\n" + "=" * 60)
    print("执行结果")
    print("=" * 60)
    print(f"\n最终 State:")
    print(f"  message: {result['message']}")
    print(f"  step_count: {result['step_count']}")


# ============================================
# 5. 流式执行（可选）
# ============================================

def run_graph_streaming(app, initial_message: str):
    """
    流式执行图（查看每一步的状态）
    
    Args:
        app: 编译后的图
        initial_message: 初始消息
    """
    print("\n" + "=" * 60)
    print("流式执行图（查看每一步）")
    print("=" * 60)
    
    # 准备初始 State
    initial_state = {
        "message": initial_message,
        "step_count": 0
    }
    
    # 流式执行
    print("\n流式输出:")
    print("-" * 60)
    for event in app.stream(initial_state):
        # event 是一个字典，键是节点名，值是该节点的输出
        for node_name, output in event.items():
            print(f"\n[节点: {node_name}]")
            print(f"  输出: {output['message']}")
            print(f"  步骤数: {output['step_count']}")
    print("-" * 60)


# ============================================
# 主函数
# ============================================

def main():
    """主函数"""
    print("\n" + "🚀 " * 30)
    print("LangGraph 简单节点图示例")
    print("🚀 " * 30)
    
    # 构建图
    app = build_graph()
    
    # 运行图
    run_graph(app, "初始消息")
    
    # 流式运行图
    run_graph_streaming(app, "流式测试")
    
    # 总结
    print("\n" + "=" * 60)
    print("📝 总结")
    print("=" * 60)
    print("""
1. 节点是普通函数，接收 State，返回 State 更新

2. 构建图的步骤：
   - 创建 StateGraph
   - 添加节点（add_node）
   - 添加边（add_edge）
   - 设置入口（set_entry_point）
   - 编译（compile）

3. 执行图：
   - invoke(): 一次性执行完成
   - stream(): 逐步执行，可以看到中间状态

4. 节点只返回需要更新的字段，不是完整 State
    """)
    print("=" * 60)


if __name__ == "__main__":
    main()
