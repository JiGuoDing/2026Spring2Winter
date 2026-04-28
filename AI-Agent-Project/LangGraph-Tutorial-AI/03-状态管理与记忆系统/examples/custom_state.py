"""
自定义 State 示例

演示内容：
1. 使用 Pydantic 定义复杂的 State Schema
2. 自定义验证逻辑
3. 嵌套数据结构
4. State 的版本控制

运行方式：
python custom_state.py
"""

from typing import TypedDict, Annotated, List, Optional
from operator import add
from datetime import datetime
from pydantic import BaseModel, Field, validator


# ============================================
# 1. 使用 TypedDict 定义复杂 State
# ============================================

class UserProfile(TypedDict, total=False):
    """用户资料（所有字段可选）"""
    user_id: str
    name: str
    email: str
    preferences: dict


class ConversationState(TypedDict):
    """对话 State"""
    # 消息历史（追加模式）
    messages: Annotated[List[dict], add]
    
    # 用户资料
    user_profile: UserProfile
    
    # 对话元数据
    metadata: dict
    
    # 对话轮数
    turn_count: int
    
    # 上下文标记
    context_tags: List[str]


def example_conversation_state():
    """示例 1: 复杂的对话 State"""
    print("=" * 60)
    print("示例 1: 复杂的对话 State")
    print("=" * 60)
    
    # 初始 State
    state: ConversationState = {
        "messages": [],
        "user_profile": {
            "user_id": "user_001",
            "name": "张三",
            "email": "zhangsan@example.com"
        },
        "metadata": {
            "session_id": "session_123",
            "started_at": datetime.now().isoformat()
        },
        "turn_count": 0,
        "context_tags": []
    }
    
    print(f"\n初始 State:")
    print(f"  用户: {state['user_profile']['name']}")
    print(f"  消息数: {len(state['messages'])}")
    print(f"  轮数: {state['turn_count']}")
    
    # 更新 State
    state["messages"].append({
        "role": "user",
        "content": "你好",
        "timestamp": datetime.now().isoformat()
    })
    state["turn_count"] += 1
    state["context_tags"].append("greeting")
    
    print(f"\n更新后的 State:")
    print(f"  消息数: {len(state['messages'])}")
    print(f"  轮数: {state['turn_count']}")
    print(f"  标签: {state['context_tags']}")


# ============================================
# 2. 使用 Pydantic 定义 State（推荐）
# ============================================

class Message(BaseModel):
    """消息模型"""
    role: str = Field(..., description="角色: user, assistant, system")
    content: str = Field(..., description="消息内容")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: Optional[dict] = Field(default=None)


class AgentStatePydantic(BaseModel):
    """使用 Pydantic 的 Agent State"""
    # 消息列表
    messages: List[Message] = Field(default_factory=list)
    
    # 用户信息
    user_id: str = Field(default="anonymous")
    session_id: str = Field(default_factory=lambda: f"session_{datetime.now().timestamp()}")
    
    # 对话统计
    turn_count: int = Field(default=0, ge=0)
    tool_call_count: int = Field(default=0, ge=0)
    
    # 上下文
    context: dict = Field(default_factory=dict)
    
    # 配置
    max_turns: int = Field(default=10, ge=1, le=100)
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    
    @validator('messages')
    def validate_messages(cls, v):
        """验证消息列表"""
        if len(v) > 100:
            raise ValueError("消息列表不能超过 100 条")
        return v
    
    @validator('turn_count')
    def validate_turns(cls, v, values):
        """验证轮数限制"""
        max_turns = values.get('max_turns', 10)
        if v > max_turns:
            raise ValueError(f"对话轮数超过限制 ({max_turns})")
        return v
    
    def add_message(self, role: str, content: str):
        """添加消息的便捷方法"""
        self.messages.append(Message(role=role, content=content))
        self.turn_count += 1
    
    def get_recent_messages(self, n: int = 10) -> List[Message]:
        """获取最近的消息"""
        return self.messages[-n:] if len(self.messages) > n else self.messages
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return self.model_dump()


def example_pydantic_state():
    """示例 2: Pydantic State"""
    print("\n" + "=" * 60)
    print("示例 2: Pydantic State（带验证）")
    print("=" * 60)
    
    # 创建 State
    state = AgentStatePydantic(
        user_id="user_001",
        max_turns=5,
        temperature=0.8
    )
    
    print(f"\n初始 State:")
    print(f"  用户: {state.user_id}")
    print(f"  最大轮数: {state.max_turns}")
    print(f"  当前轮数: {state.turn_count}")
    
    # 添加消息
    state.add_message("user", "你好")
    state.add_message("assistant", "你好！有什么可以帮助你的？")
    state.add_message("user", "北京天气怎么样？")
    
    print(f"\n添加消息后:")
    print(f"  消息数: {len(state.messages)}")
    print(f"  轮数: {state.turn_count}")
    
    # 获取最近消息
    recent = state.get_recent_messages(2)
    print(f"\n最近 2 条消息:")
    for msg in recent:
        print(f"  [{msg.role}] {msg.content}")
    
    # 验证示例
    print(f"\n验证测试:")
    try:
        # 这会失败，因为 temperature 必须在 0-1 之间
        invalid_state = AgentStatePydantic(temperature=1.5)
    except Exception as e:
        print(f"  ✓ 验证生效: {type(e).__name__}")
    
    # 转换为字典
    print(f"\n转换为字典:")
    state_dict = state.to_dict()
    print(f"  键: {list(state_dict.keys())}")


# ============================================
# 3. State 的版本控制
# ============================================

class VersionedState(TypedDict):
    """带版本控制的 State"""
    # State 版本
    version: int
    
    # 实际数据
    data: dict
    
    # 变更历史
    history: List[dict]


def create_versioned_state(data: dict) -> VersionedState:
    """创建版本化 State"""
    return {
        "version": 1,
        "data": data,
        "history": [{
            "version": 1,
            "timestamp": datetime.now().isoformat(),
            "action": "create"
        }]
    }


def update_versioned_state(state: VersionedState, new_data: dict) -> VersionedState:
    """更新版本化 State"""
    new_version = state["version"] + 1
    
    # 深拷贝数据
    updated_data = state["data"].copy()
    updated_data.update(new_data)
    
    # 记录历史
    history_entry = {
        "version": new_version,
        "timestamp": datetime.now().isoformat(),
        "action": "update",
        "changes": list(new_data.keys())
    }
    
    return {
        "version": new_version,
        "data": updated_data,
        "history": state["history"] + [history_entry]
    }


def example_versioned_state():
    """示例 3: 版本控制"""
    print("\n" + "=" * 60)
    print("示例 3: State 版本控制")
    print("=" * 60)
    
    # 创建初始 State
    state = create_versioned_state({
        "user_id": "user_001",
        "name": "张三",
        "preferences": {"theme": "dark"}
    })
    
    print(f"\n版本 {state['version']}:")
    print(f"  数据: {state['data']}")
    
    # 第一次更新
    state = update_versioned_state(state, {
        "name": "张三（已更新）",
        "email": "zhangsan@example.com"
    })
    
    print(f"\n版本 {state['version']}:")
    print(f"  数据: {state['data']}")
    
    # 第二次更新
    state = update_versioned_state(state, {
        "preferences": {"theme": "light", "language": "zh-CN"}
    })
    
    print(f"\n版本 {state['version']}:")
    print(f"  数据: {state['data']}")
    
    # 查看历史
    print(f"\n变更历史:")
    for entry in state["history"]:
        print(f"  v{entry['version']}: {entry['action']} at {entry['timestamp']}")


# ============================================
# 4. State 的序列化和反序列化
# ============================================

def serialize_state(state: dict) -> str:
    """序列化 State 为 JSON 字符串"""
    import json
    # 处理 datetime 对象
    def json_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    return json.dumps(state, default=json_serializer, ensure_ascii=False, indent=2)


def deserialize_state(json_str: str) -> dict:
    """从 JSON 字符串反序列化 State"""
    import json
    return json.loads(json_str)


def example_serialization():
    """示例 4: 序列化"""
    print("\n" + "=" * 60)
    print("示例 4: State 序列化和反序列化")
    print("=" * 60)
    
    # 原始 State
    state = {
        "user_id": "user_001",
        "messages": [
            {"role": "user", "content": "你好", "timestamp": datetime.now()}
        ],
        "metadata": {
            "session_start": datetime.now()
        }
    }
    
    print(f"\n原始 State:")
    print(f"  类型: {type(state)}")
    print(f"  用户: {state['user_id']}")
    
    # 序列化
    json_str = serialize_state(state)
    print(f"\n序列化后 (JSON):")
    print(json_str[:200] + "...")
    
    # 反序列化
    restored = deserialize_state(json_str)
    print(f"\n反序列化后:")
    print(f"  类型: {type(restored)}")
    print(f"  用户: {restored['user_id']}")


# ============================================
# 主函数
# ============================================

def main():
    """主函数"""
    print("\n" + "🚀 " * 30)
    print("LangGraph 自定义 State 示例")
    print("🚀 " * 30)
    
    # 运行示例
    example_conversation_state()
    example_pydantic_state()
    example_versioned_state()
    example_serialization()
    
    # 总结
    print("\n" + "=" * 60)
    print("📝 总结")
    print("=" * 60)
    print("""
1. State 设计原则：
   - 最小化：只包含必要的字段
   - 可扩展：预留扩展空间
   - 类型安全：使用 TypedDict 或 Pydantic

2. TypedDict vs Pydantic：
   - TypedDict：轻量，适合简单场景
   - Pydantic：强大，支持验证和默认值

3. 最佳实践：
   - 使用 Annotated 和 reducer 控制更新行为
   - 实现验证逻辑防止无效状态
   - 记录变更历史便于调试
   - 支持序列化便于持久化
    """)
    print("=" * 60)


if __name__ == "__main__":
    main()
