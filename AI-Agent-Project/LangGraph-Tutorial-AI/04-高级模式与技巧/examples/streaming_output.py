"""
流式输出示例

演示内容：
1. invoke() vs stream()
2. stream_mode 的不同选项
3. 实时显示工具调用
4. 流式文本输出

运行方式：
python streaming_output.py
"""

from typing import TypedDict, Annotated, List
from operator import add
import time

from langgraph.graph import StateGraph, END


# ============================================
# 1. 定义 State
# ============================================

class StreamState(TypedDict):
    """流式输出的 State"""
    messages: Annotated[List[str], add]
    step: int
    data: dict


# ============================================
# 2. 定义节点（模拟耗时操作）
# ============================================

def step_1(state: StreamState) -> dict:
    """步骤 1：数据收集"""
    print("[步骤 1] 开始收集数据...")
    time.sleep(1)  # 模拟耗时操作
    
    return {
        "messages": ["步骤 1 完成：数据收集"],
        "step": 1,
        "data": {"collected": True}
    }


def step_2(state: StreamState) -> dict:
    """步骤 2：数据处理"""
    print("[步骤 2] 开始处理数据...")
    time.sleep(1)
    
    return {
        "messages": ["步骤 2 完成：数据处理"],
        "step": 2,
        "data": {**state["data"], "processed": True}
    }


def step_3(state: StreamState) -> dict:
    """步骤 3：生成结果"""
    print("[步骤 3] 开始生成结果...")
    time.sleep(1)
    
    return {
        "messages": ["步骤 3 完成：结果生成"],
        "step": 3,
        "data": {**state["data"], "completed": True}
    }


# ============================================
# 3. 构建图
# ============================================

def build_stream_graph():
    """构建流式图"""
    graph = StateGraph(StreamState)
    
    graph.add_node("step_1", step_1)
    graph.add_node("step_2", step_2)
    graph.add_node("step_3", step_3)
    
    graph.add_edge("step_1", "step_2")
    graph.add_edge("step_2", "step_3")
    graph.add_edge("step_3", END)
    
    graph.set_entry_point("step_1")
    
    app = graph.compile()
    return app


# ============================================
# 4. invoke() vs stream()
# ============================================

def example_invoke():
    """示例 1: 使用 invoke() - 等待完成"""
    print("\n" + "=" * 60)
    print("示例 1: invoke() - 等待所有步骤完成")
    print("=" * 60)
    
    app = build_stream_graph()
    
    initial_state = {
        "messages": [],
        "step": 0,
        "data": {}
    }
    
    print("\n开始执行（等待完成）...")
    print("-" * 60)
    
    # invoke 会等待所有步骤完成
    result = app.invoke(initial_state)
    
    print("-" * 60)
    print("\n执行完成！")
    print(f"最终结果: {result}")


def example_stream():
    """示例 2: 使用 stream() - 实时输出"""
    print("\n" + "=" * 60)
    print("示例 2: stream() - 实时查看每个步骤")
    print("=" * 60)
    
    app = build_stream_graph()
    
    initial_state = {
        "messages": [],
        "step": 0,
        "data": {}
    }
    
    print("\n开始流式执行:")
    print("-" * 60)
    
    # stream 会逐步返回每个节点的结果
    for event in app.stream(initial_state):
        # event 是字典，键是节点名，值是节点输出
        for node_name, output in event.items():
            print(f"\n✓ 节点完成: {node_name}")
            print(f"  消息: {output['messages'][-1]}")
            print(f"  步骤: {output['step']}")
            print(f"  数据: {output['data']}")
    
    print("-" * 60)
    print("\n流式执行完成！")


# ============================================
# 5. stream_mode 详解
# ============================================

def example_stream_modes():
    """示例 3: 不同的 stream_mode"""
    print("\n" + "=" * 60)
    print("示例 3: 不同的 stream_mode")
    print("=" * 60)
    
    app = build_stream_graph()
    
    initial_state = {
        "messages": ["开始"],
        "step": 0,
        "data": {}
    }
    
    # Mode 1: values（默认）- 返回完整的 State
    print("\n--- Mode: values (完整 State) ---")
    for event in app.stream(initial_state, stream_mode="values"):
        print(f"State 更新: step={event.get('step')}, messages={len(event.get('messages', []))}")
    
    # Mode 2: updates - 只返回节点的更新
    print("\n--- Mode: updates (节点更新) ---")
    for event in app.stream(initial_state, stream_mode="updates"):
        for node_name, update in event.items():
            print(f"节点 {node_name} 更新: {update['messages']}")
    
    # Mode 3: debug - 调试信息
    print("\n--- Mode: debug (调试信息) ---")
    for event in app.stream(initial_state, stream_mode="debug"):
        print(f"调试: {event['type']} - {event.get('node', 'N/A')}")


# ============================================
# 6. 实时进度显示
# ============================================

def example_progress_bar():
    """示例 4: 显示进度条"""
    print("\n" + "=" * 60)
    print("示例 4: 实时进度显示")
    print("=" * 60)
    
    app = build_stream_graph()
    
    initial_state = {
        "messages": [],
        "step": 0,
        "data": {}
    }
    
    total_steps = 3
    current_step = 0
    
    print("\n执行进度:")
    
    for event in app.stream(initial_state):
        for node_name, output in event.items():
            current_step += 1
            progress = (current_step / total_steps) * 100
            
            # 显示进度条
            bar_length = 30
            filled = int(bar_length * current_step / total_steps)
            bar = "█" * filled + "░" * (bar_length - filled)
            
            print(f"\r[{bar}] {progress:.0f}% - 完成: {node_name}", end="", flush=True)
            time.sleep(0.1)
    
    print("\n\n✓ 所有步骤完成！")


# ============================================
# 7. 条件流的流式输出
# ============================================

def example_conditional_stream():
    """示例 5: 条件流的流式输出"""
    print("\n" + "=" * 60)
    print("示例 5: 条件流的流式输出")
    print("=" * 60)
    
    from typing import Literal
    
    class CondState(TypedDict):
        messages: Annotated[List[str], add]
        score: int
    
    def evaluate(state: CondState) -> dict:
        score = state["score"]
        print(f"\n[评估] 分数: {score}")
        return {"messages": [f"评估完成: {score}分"]}
    
    def pass_node(state: CondState) -> dict:
        print("[通过] 恭喜！")
        return {"messages": ["✓ 通过"]}
    
    def fail_node(state: CondState) -> dict:
        print("[失败] 需要努力！")
        return {"messages": ["✗ 失败"]}
    
    def check_score(state: CondState) -> Literal["pass", "fail"]:
        return "pass" if state["score"] >= 60 else "fail"
    
    # 构建图
    graph = StateGraph(CondState)
    graph.add_node("evaluate", evaluate)
    graph.add_node("pass", pass_node)
    graph.add_node("fail", fail_node)
    
    graph.add_edge("evaluate", "pass")
    graph.add_edge("evaluate", "fail")
    graph.add_conditional_edges("evaluate", check_score)
    graph.set_entry_point("evaluate")
    graph.add_edge("pass", END)
    graph.add_edge("fail", END)
    
    app = graph.compile()
    
    # 场景 1: 通过
    print("\n--- 场景 1: 分数 80 (通过) ---")
    for event in app.stream({"messages": [], "score": 80}):
        for node_name, output in event.items():
            print(f"  节点: {node_name}, 输出: {output['messages']}")
    
    # 场景 2: 失败
    print("\n--- 场景 2: 分数 40 (失败) ---")
    for event in app.stream({"messages": [], "score": 40}):
        for node_name, output in event.items():
            print(f"  节点: {node_name}, 输出: {output['messages']}")


# ============================================
# 主函数
# ============================================

def main():
    """主函数"""
    print("\n" + "🚀 " * 30)
    print("LangGraph 流式输出示例")
    print("🚀 " * 30)
    
    # 运行示例
    example_invoke()
    example_stream()
    example_stream_modes()
    example_progress_bar()
    example_conditional_stream()
    
    # 总结
    print("\n" + "=" * 60)
    print("📝 总结")
    print("=" * 60)
    print("""
1. invoke() vs stream():
   - invoke(): 等待所有步骤完成，返回最终结果
   - stream(): 逐步返回每个节点的结果

2. stream_mode 选项：
   - values: 返回完整的 State（默认）
   - updates: 只返回节点的更新
   - debug: 返回调试信息

3. 使用场景：
   - invoke(): 简单场景，只需最终结果
   - stream(): 需要实时反馈、进度显示

4. 最佳实践：
   - 长时间任务使用 stream()
   - 实时显示进度给用户
   - 使用合适的 stream_mode
   - 处理异常情况
    """)
    print("=" * 60)


if __name__ == "__main__":
    main()
