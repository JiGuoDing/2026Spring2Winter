# 第三章：Agent 开发实战

## 3.1 Agent 架构设计

### 基础 Agent 组件

一个完整的 Agent 通常包含以下组件：

```python
class BasicAgent:
    def __init__(self):
        self.client = OpenAI()
        self.messages = []
        self.tools = []
        
    def add_tool(self, tool):
        """添加工具"""
        self.tools.append(tool)
        
    def add_message(self, role, content):
        """添加消息到历史"""
        self.messages.append({"role": role, "content": content})
        
    def chat(self, user_input):
        """对话核心方法"""
        self.add_message("user", user_input)
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=self.messages,
            tools=self.tools if self.tools else None
        )
        
        assistant_message = response.choices[0].message
        self.add_message("assistant", assistant_message.content)
        
        return assistant_message
```

## 3.2 工具系统集成

### 创建工具装饰器

```python
from functools import wraps
import json

def tool(description: str, parameters: dict):
    """工具装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        wrapper.__tool_spec__ = {
            "type": "function",
            "function": {
                "name": func.__name__,
                "description": description,
                "parameters": parameters
            }
        }
        return wrapper
    return decorator

# 使用示例
@tool(
    description="搜索网络信息",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"}
        },
        "required": ["query"]
    }
)
def search_web(query):
    return f"搜索结果：关于{query}的信息"
```

### 工具管理器

```python
class ToolManager:
    def __init__(self):
        self.tools = {}
        
    def register(self, func):
        """注册工具"""
        spec = func.__tool_spec__
        name = func.__name__
        self.tools[name] = {
            "spec": spec,
            "func": func
        }
        return func
        
    def get_specs(self):
        """获取所有工具规格"""
        return [t["spec"] for t in self.tools.values()]
        
    def execute(self, name, arguments):
        """执行工具"""
        if name not in self.tools:
            raise ValueError(f"未知工具：{name}")
        return self.tools[name]["func"](**arguments)

# 使用
tool_manager = ToolManager()
tool_manager.register(search_web)
```

## 3.3 记忆系统实现

### 短期记忆（对话历史）

```python
class ShortTermMemory:
    def __init__(self, max_messages=10):
        self.messages = []
        self.max_messages = max_messages
        
    def add(self, role, content):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        
        # 限制消息数量
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
            
    def get_all(self):
        return [{"role": m["role"], "content": m["content"]} 
                for m in self.messages]
                
    def clear(self):
        self.messages = []
```

### 长期记忆（向量数据库）

```python
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class LongTermMemory:
    def __init__(self):
        self.memories = []
        self.embeddings = []
        self.client = OpenAI()
        
    def add(self, text):
        """添加记忆"""
        # 获取嵌入
        response = self.client.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        embedding = response.data[0].embedding
        
        self.memories.append(text)
        self.embeddings.append(embedding)
        
    def search(self, query, top_k=3):
        """搜索相关记忆"""
        # 获取查询嵌入
        response = self.client.embeddings.create(
            model="text-embedding-ada-002",
            input=query
        )
        query_embedding = response.data[0].embedding
        
        # 计算相似度
        similarities = []
        for i, emb in enumerate(self.embeddings):
            sim = cosine_similarity([query_embedding], [emb])[0][0]
            similarities.append((i, sim))
            
        # 排序并返回 top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return [self.memories[i] for i, _ in similarities[:top_k]]
```

## 3.4 多轮对话管理

### 对话状态跟踪

```python
class ConversationState:
    def __init__(self):
        self.current_topic = None
        self.entities = {}
        self.intent = None
        self.slots = {}
        
    def update(self, message):
        """更新状态"""
        # 可以使用另一个 LLM 调用来提取状态
        pass
        
    def is_complete(self):
        """检查当前意图是否完成"""
        return all(self.slots.values())
```

### 上下文管理

```python
class ContextManager:
    def __init__(self):
        self.contexts = {}
        self.active_context = None
        
    def set(self, key, value):
        self.contexts[key] = value
        
    def get(self, key, default=None):
        return self.contexts.get(key, default)
        
    def delete(self, key):
        if key in self.contexts:
            del self.contexts[key]
            
    def clear(self):
        self.contexts = {}
```

## 3.5 完整 Agent 示例

### 智能助手 Agent

```python
class AssistantAgent:
    def __init__(self, name="助手"):
        self.name = name
        self.client = OpenAI()
        self.tool_manager = ToolManager()
        self.memory = ShortTermMemory()
        self.long_term_memory = LongTermMemory()
        
        # 初始化系统提示
        self.system_prompt = f"""你是{name},一个智能助手。
你可以帮助用户解答问题、执行任务。
你可以使用以下工具：
- search_web: 搜索网络信息
- calculate: 计算数学表达式
- get_time: 获取当前时间
"""
        
    def register_tools(self):
        """注册工具"""
        @tool(
            description="搜索网络信息",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"}
                },
                "required": ["query"]
            }
        )
        def search_web(query):
            return f"搜索结果：关于{query}的信息"
            
        @tool(
            description="计算数学表达式",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "数学表达式，如：2+2*3"}
                },
                "required": ["expression"]
            }
        )
        def calculate(expression):
            try:
                result = eval(expression)
                return f"计算结果：{result}"
            except Exception as e:
                return f"计算错误：{e}"
                
        self.tool_manager.register(search_web)
        self.tool_manager.register(calculate)
        
    def chat(self, user_input):
        """对话主逻辑"""
        # 添加到记忆
        self.memory.add("user", user_input)
        
        # 构建消息
        messages = [
            {"role": "system", "content": self.system_prompt},
            *self.memory.get_all()
        ]
        
        # 调用 LLM
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            tools=self.tool_manager.get_specs()
        )
        
        assistant_message = response.choices[0].message
        
        # 处理工具调用
        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                
                # 执行工具
                result = self.tool_manager.execute(name, args)
                
                # 添加工具响应
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
                
            # 再次调用获取最终回复
            final_response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages
            )
            assistant_message = final_response.choices[0].message
            
        # 保存回复
        self.memory.add("assistant", assistant_message.content)
        
        # 保存到长期记忆
        self.long_term_memory.add(user_input)
        
        return assistant_message.content
        
    def run(self):
        """运行交互式对话"""
        print(f"{self.name}: 你好！我是{name}，有什么可以帮助你的？")
        
        while True:
            try:
                user_input = input("你：").strip()
                if user_input.lower() in ["退出", "bye", "quit"]:
                    print(f"{self.name}: 再见！")
                    break
                    
                response = self.chat(user_input)
                print(f"{self.name}: {response}")
                
            except Exception as e:
                print(f"{self.name}: 抱歉，我遇到了一些问题：{e}")

# 运行
if __name__ == "__main__":
    agent = AssistantAgent(name="小智")
    agent.register_tools()
    agent.run()
```

## 3.6 任务规划 Agent

```python
class TaskPlannerAgent:
    def __init__(self):
        self.client = OpenAI()
        
    def plan(self, task):
        """将复杂任务分解为步骤"""
        prompt = f"""请将以下任务分解为可执行的步骤：
任务：{task}

请以 JSON 格式返回步骤列表：
{{
    "steps": [
        {{"step": 1, "action": "...", "description": "..."}},
        {{"step": 2, "action": "...", "description": "..."}}
    ]
}}
"""
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
        
    def execute_plan(self, plan):
        """执行计划"""
        results = []
        for step in plan["steps"]:
            print(f"执行步骤 {step['step']}: {step['action']}")
            # 这里可以调用相应的工具或 API
            results.append(f"步骤{step['step']}完成")
        return results
```

## 练习题

1. 实现一个简单的问答 Agent
2. 为你的 Agent 添加自定义工具
3. 实现记忆系统（短期 + 长期）
4. 创建一个任务规划 Agent

## 下一步

继续学习 [进阶技巧](../04-进阶技巧/README.md)
