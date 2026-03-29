from openai import OpenAI
import json
import time

class ToolManager:
    """工具管理器"""
    def __init__(self):
        self.tools = {}
        
    def register(self, func):
        """注册工具"""
        if hasattr(func, '__tool_spec__'):
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

def tool(description: str, parameters: dict):
    """工具装饰器"""
    from functools import wraps
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

class ShortTermMemory:
    """短期记忆管理"""
    def __init__(self, max_messages=10):
        self.messages = []
        self.max_messages = max_messages
        
    def add(self, role, content):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
            
    def get_all(self):
        return [{"role": m["role"], "content": m["content"]} 
                for m in self.messages]
                
    def clear(self):
        self.messages = []

class AssistantAgent:
    """智能助手 Agent"""
    def __init__(self, name="助手"):
        self.name = name
        self.client = OpenAI()
        self.tool_manager = ToolManager()
        self.memory = ShortTermMemory()
        
        self.system_prompt = f"""你是{name},一个智能助手。
你可以帮助用户解答问题、执行任务。
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
        self.memory.add("user", user_input)
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            *self.memory.get_all()
        ]
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            tools=self.tool_manager.get_specs()
        )
        
        assistant_message = response.choices[0].message
        
        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                
                result = self.tool_manager.execute(name, args)
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
                
            final_response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages
            )
            assistant_message = final_response.choices[0].message
            
        self.memory.add("assistant", assistant_message.content)
        
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

if __name__ == "__main__":
    agent = AssistantAgent(name="小智")
    agent.register_tools()
    print("=== 简易 Agent 演示 ===")
    agent.run()
