"""
State 基础示例

演示内容：
1. 使用 TypedDict 定义 State
2. State 的创建和更新
3. Reducer 函数的使用（operator.add, operator.replace）
4. 自定义 reducer

运行方式：
python basic_state.py
"""

from typing import TypedDict, Annotated, List
from operator import add, replace


# ============================================
# 1. 使用 TypedDict 定义基础 State
# ============================================

class BasicState(TypedDict):
    """基础 State 定义"""
    message: str        # 当前消息
    count: int          # 计数器
    history: List[str]  # 历史记录


def example_basic_state():
    """示例 1: 基础 State 的创建和更新"""
    print("=" * 60)
    print("示例 1: 基础 State 的创建和更新")
    print("=" * 60)
    
    # 创建初始 State
    state: BasicState = {
        "message": "Hello, LangGraph!",
        "count": 0,
        "history": []
    }
    print(f"\n初始 State:")
    print(f"  message: {state['message']}")
    print(f"  count: {state['count']}")
    print(f"  history: {state['history']}")
    
    # 更新 State（只更新部分字段）
    state["message"] = "Updated message"
    state["count"] = 1
    state["history"].append("First update")
    
    print(f"\n更新后的 State:")
    print(f"  message: {state['message']}")
    print(f"  count: {state['count']}")
    print(f"  history: {state['history']}")


# ============================================
# 2. 使用 Annotated 和 Reducer
# ============================================

class StateWithReducer(TypedDict):
    """使用 Reducer 的 State 定义"""
    # 使用 add reducer：新值会追加到列表
    messages: Annotated[List[str], add]
    
    # 使用 replace reducer：新值会替换旧值（默认行为）
    current_message: Annotated[str, replace]
    
    # 计数器：每次增加
    counter: Annotated[int, add]


def example_reducer():
    """示例 2: Reducer 函数的使用"""
    print("\n" + "=" * 60)
    print("示例 2: Reducer 函数的使用")
    print("=" * 60)
    
    # 初始 State
    state: StateWithReducer = {
        "messages": ["Initial message"],
        "current_message": "Start",
        "counter": 0
    }
    print(f"\n初始 State:")
    print(f"  messages: {state['messages']}")
    print(f"  current_message: {state['current_message']}")
    print(f"  counter: {state['counter']}")
    
    # 第一次更新
    update1 = {
        "messages": ["Message 1"],      # add: 追加
        "current_message": "Update 1",  # replace: 替换
        "counter": 1                    # add: 增加
    }
    
    # 模拟 LangGraph 的 State 更新逻辑
    new_state = state.copy()
    new_state["messages"] = state["messages"] + update1["messages"]
    new_state["current_message"] = update1["current_message"]
    new_state["counter"] = state["counter"] + update1["counter"]
    
    print(f"\n第一次更新后:")
    print(f"  messages: {new_state['messages']}")
    print(f"  current_message: {new_state['current_message']}")
    print(f"  counter: {new_state['counter']}")
    
    # 第二次更新
    update2 = {
        "messages": ["Message 2"],
        "current_message": "Update 2",
        "counter": 2
    }
    
    # 再次更新
    new_state["messages"] = new_state["messages"] + update2["messages"]
    new_state["current_message"] = update2["current_message"]
    new_state["counter"] = new_state["counter"] + update2["counter"]
    
    print(f"\n第二次更新后:")
    print(f"  messages: {new_state['messages']}")
    print(f"  current_message: {new_state['current_message']}")
    print(f"  counter: {new_state['counter']}")


# ============================================
# 3. 自定义 Reducer
# ============================================

def custom_reducer(existing: List[int], update: int) -> List[int]:
    """
    自定义 reducer：只保留最大的 3 个数字
    
    Args:
        existing: 现有的数字列表
        update: 新添加的数字
    
    Returns:
        更新后的列表（只保留最大的 3 个）
    """
    combined = existing + [update]
    return sorted(combined, reverse=True)[:3]


class StateWithCustomReducer(TypedDict):
    """使用自定义 Reducer 的 State"""
    top_numbers: Annotated[List[int], custom_reducer]


def example_custom_reducer():
    """示例 3: 自定义 Reducer"""
    print("\n" + "=" * 60)
    print("示例 3: 自定义 Reducer（保留最大的 3 个数字）")
    print("=" * 60)
    
    # 初始 State
    state: StateWithCustomReducer = {
        "top_numbers": []
    }
    print(f"\n初始 State:")
    print(f"  top_numbers: {state['top_numbers']}")
    
    # 逐步添加数字
    numbers = [5, 2, 8, 1, 9, 3, 7]
    
    for num in numbers:
        old_state = state.copy()
        state["top_numbers"] = custom_reducer(state["top_numbers"], num)
        print(f"添加数字 {num}: {old_state['top_numbers']} → {state['top_numbers']}")
    
    print(f"\n最终结果（最大的 3 个数字）:")
    print(f"  top_numbers: {state['top_numbers']}")


# ============================================
# 4. 使用 Pydantic 定义 State（可选）
# ============================================

from pydantic import BaseModel, Field
from typing import Optional


class PydanticState(BaseModel):
    """使用 Pydantic 定义 State（支持验证和默认值）"""
    message: str = Field(default="", description="当前消息")
    count: int = Field(default=0, ge=0, description="计数器（非负）")
    history: List[str] = Field(default_factory=list, description="历史记录")
    metadata: Optional[dict] = Field(default=None, description="元数据")


def example_pydantic_state():
    """示例 4: 使用 Pydantic 定义 State"""
    print("\n" + "=" * 60)
    print("示例 4: 使用 Pydantic 定义 State")
    print("=" * 60)
    
    # 创建 State（带验证）
    state = PydanticState(
        message="Hello",
        count=0,
        history=["init"]
    )
    print(f"\n初始 State:")
    print(f"  message: {state.message}")
    print(f"  count: {state.count}")
    print(f"  history: {state.history}")
    
    # 更新 State
    state.message = "Updated"
    state.count += 1
    state.history.append("update")
    
    print(f"\n更新后的 State:")
    print(f"  message: {state.message}")
    print(f"  count: {state.count}")
    print(f"  history: {state.history}")
    
    # Pydantic 验证示例
    try:
        # 这会失败，因为 count 必须 >= 0
        invalid_state = PydanticState(count=-1)
    except Exception as e:
        print(f"\n✓ Pydantic 验证生效：{type(e).__name__}")


# ============================================
# 主函数
# ============================================

def main():
    """运行所有示例"""
    print("\n" + "🚀 " * 30)
    print("LangGraph State 基础示例")
    print("🚀 " * 30 + "\n")
    
    # 运行示例
    example_basic_state()
    example_reducer()
    example_custom_reducer()
    example_pydantic_state()
    
    # 总结
    print("\n" + "=" * 60)
    print("📝 总结")
    print("=" * 60)
    print("""
1. State 是 LangGraph 中的数据容器，用于在节点间传递信息

2. 定义 State 的方式：
   - TypedDict（推荐，简单轻量）
   - Pydantic（支持验证和默认值）

3. Reducer 函数控制 State 如何更新：
   - operator.add：追加/累加
   - operator.replace：替换（默认）
   - 自定义 reducer：实现复杂逻辑

4. 在 LangGraph 中：
   - 节点接收 State 作为输入
   - 节点返回 State 的更新（部分字段）
   - LangGraph 使用 reducer 合并更新
    """)
    print("=" * 60)


if __name__ == "__main__":
    main()
