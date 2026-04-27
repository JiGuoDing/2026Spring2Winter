"""
条件边示例

演示内容：
1. 条件边的定义和使用
2. 根据状态动态选择下一个节点
3. 条件函数的编写
4. 实际应用：简单的决策流程

运行方式：
python conditional_edge.py
"""

from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END


# ============================================
# 1. 定义 State
# ============================================

class DecisionState(TypedDict):
    """决策流程的 State"""
    question: str       # 问题
    answer: str         # 答案
    score: int          # 分数
    step: int           # 当前步骤
    history: list       # 历史记录


# ============================================
# 2. 定义节点函数
# ============================================

def ask_question(state: DecisionState) -> dict:
    """节点 1：提出问题"""
    print(f"\n[提问节点] 问题: {state['question']}")
    
    # 这里简化处理，实际中可能是用户输入或模型生成
    score = state.get('score', 0)
    
    return {
        "answer": f"回答: {state['question']}",
        "step": state["step"] + 1,
        "history": state["history"] + [f"提问: {state['question']}"]
    }


def evaluate_answer(state: DecisionState) -> dict:
    """节点 2：评估答案"""
    print(f"\n[评估节点] 评估答案...")
    
    # 模拟评估逻辑
    score = state.get('score', 0)
    
    return {
        "score": score,
        "step": state["step"] + 1,
        "history": state["history"] + [f"评估得分: {score}"]
    }


def pass_result(state: DecisionState) -> dict:
    """节点 3：通过"""
    print(f"\n[通过节点] ✓ 答案通过！")
    
    return {
        "step": state["step"] + 1,
        "history": state["history"] + ["结果: 通过"]
    }


def fail_result(state: DecisionState) -> dict:
    """节点 4：失败"""
    print(f"\n[失败节点] ✗ 答案未通过，需要重新回答")
    
    return {
        "step": state["step"] + 1,
        "history": state["history"] + ["结果: 失败"]
    }


def final_summary(state: DecisionState) -> dict:
    """节点 5：总结"""
    print(f"\n[总结节点] 生成最终总结")
    
    summary = f"""
    流程完成！
    - 问题: {state['question']}
    - 得分: {state['score']}
    - 步骤数: {state['step']}
    - 历史: {len(state['history'])} 条记录
    """
    
    return {
        "history": state["history"] + [summary]
    }


# ============================================
# 3. 定义条件函数
# ============================================

def check_score(state: DecisionState) -> Literal["pass", "fail"]:
    """
    条件函数：根据分数决定下一步
    
    Args:
        state: 当前状态
    
    Returns:
        下一个节点的名称
    """
    score = state.get("score", 0)
    print(f"\n[条件判断] 当前分数: {score}")
    
    if score >= 60:
        print("[条件判断] → 选择: pass")
        return "pass"
    else:
        print("[条件判断] → 选择: fail")
        return "fail"


def check_retry(state: DecisionState) -> Literal["retry", "finish"]:
    """
    条件函数：是否需要重试
    
    Args:
        state: 当前状态
    
    Returns:
        下一个节点的名称
    """
    score = state.get("score", 0)
    step = state.get("step", 0)
    
    print(f"\n[重试判断] 分数: {score}, 步骤: {step}")
    
    # 如果失败且步骤数小于 3，允许重试
    if score < 60 and step < 3:
        print("[重试判断] → 选择: retry（重新提问）")
        return "retry"
    else:
        print("[重试判断] → 选择: finish（进入总结）")
        return "finish"


# ============================================
# 4. 构建图
# ============================================

def build_decision_graph():
    """
    构建决策流程图
    
    流程：
    ask_question → evaluate_answer → [check_score]
                                        ↓
                            ┌───────────┴───────────┐
                            ↓                       ↓
                          pass                    fail
                            ↓                       ↓
                    [check_retry]              [check_retry]
                        ↓  ↓                      ↓   ↓
                      retry finish              retry finish
                        ↓    ↓                    ↓     ↓
                    ask_question finish      ask_question finish
                                                ↓
                                              finish → final_summary
    """
    print("\n" + "=" * 60)
    print("构建决策流程图")
    print("=" * 60)
    
    # 创建 StateGraph
    graph = StateGraph(DecisionState)
    print("\n✓ 创建 StateGraph")
    
    # 添加节点
    graph.add_node("ask", ask_question)
    graph.add_node("evaluate", evaluate_answer)
    graph.add_node("pass", pass_result)
    graph.add_node("fail", fail_result)
    graph.add_node("summary", final_summary)
    print("✓ 添加节点: ask, evaluate, pass, fail, summary")
    
    # 添加普通边
    graph.add_edge("ask", "evaluate")  # 提问后评估
    graph.add_edge("pass", "summary")  # 通过后总结
    graph.add_edge("fail", "summary")  # 失败后也总结
    print("✓ 添加普通边")
    
    # 添加条件边（根据分数选择 pass 或 fail）
    graph.add_conditional_edges(
        "evaluate",           # 从 evaluate 节点
        check_score,          # 条件函数
        {
            "pass": "pass",   # 如果返回 "pass"，去 pass 节点
            "fail": "fail"    # 如果返回 "fail"，去 fail 节点
        }
    )
    print("✓ 添加条件边: evaluate → [pass/fail]")
    
    # 设置入口节点
    graph.set_entry_point("ask")
    print("✓ 设置入口节点: ask")
    
    # 编译图
    app = graph.compile()
    print("✓ 编译图完成")
    
    return app


# ============================================
# 5. 运行图
# ============================================

def run_scenario(app, question: str, score: int):
    """
    运行一个场景
    
    Args:
        app: 编译后的图
        question: 问题
        score: 模拟分数
    """
    print("\n" + "=" * 60)
    print(f"场景: {question} (分数: {score})")
    print("=" * 60)
    
    # 初始 State
    initial_state = {
        "question": question,
        "answer": "",
        "score": score,
        "step": 0,
        "history": []
    }
    
    print(f"\n初始 State:")
    print(f"  question: {initial_state['question']}")
    print(f"  score: {initial_state['score']}")
    print(f"  step: {initial_state['step']}")
    
    # 执行
    print("\n开始执行...")
    print("-" * 60)
    result = app.invoke(initial_state)
    print("-" * 60)
    
    # 输出结果
    print("\n" + "=" * 60)
    print("执行结果")
    print("=" * 60)
    print(f"\n最终 State:")
    print(f"  question: {result['question']}")
    print(f"  score: {result['score']}")
    print(f"  step: {result['step']}")
    print(f"\n历史记录:")
    for i, record in enumerate(result['history'], 1):
        print(f"  {i}. {record}")


# ============================================
# 主函数
# ============================================

def main():
    """主函数"""
    print("\n" + "🚀 " * 30)
    print("LangGraph 条件边示例")
    print("🚀 " * 30)
    
    # 构建图
    app = build_decision_graph()
    
    # 场景 1：分数 >= 60（通过）
    run_scenario(app, "什么是 Python？", 80)
    
    # 场景 2：分数 < 60（失败）
    run_scenario(app, "什么是机器学习？", 40)
    
    # 总结
    print("\n" + "=" * 60)
    print("📝 总结")
    print("=" * 60)
    print("""
1. 条件边允许根据状态动态选择下一个节点

2. 条件函数：
   - 接收当前 State
   - 返回下一个节点的名称（字符串）
   - 使用 Literal 类型提示可能的返回值

3. add_conditional_edges 参数：
   - 第一个参数：源节点
   - 第二个参数：条件函数
   - 第三个参数：映射字典（返回值 → 节点名）

4. 常见应用：
   - 根据模型输出决定下一步
   - 检查工具调用结果
   - 实现循环和重试逻辑
    """)
    print("=" * 60)


if __name__ == "__main__":
    main()
