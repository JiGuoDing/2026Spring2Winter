"""
实用工具集 - OpenAI 开发中常用的辅助函数
"""

import os
import json
import tiktoken
from typing import List, Dict
from openai import OpenAI


class TokenCounter:
    """Token 计数器"""
    
    def __init__(self):
        self.client = OpenAI()
        
    def count(self, text: str, model: str = "gpt-3.5-turbo") -> int:
        """计算文本的 token 数量"""
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    
    def count_messages(self, messages: List[Dict], model: str = "gpt-3.5-turbo") -> int:
        """计算消息列表的 token 数量"""
        encoding = tiktoken.encoding_for_model(model)
        
        total_tokens = 0
        for message in messages:
            # 每条消息的基础开销
            total_tokens += 4
            
            for key, value in message.items():
                total_tokens += len(encoding.encode(value))
                
                if key == "name":
                    total_tokens -= 1
                    
        # 每条回复的额外开销
        total_tokens += 2
        
        return total_tokens
    
    def estimate_cost(self, tokens: int, model: str = "gpt-3.5-turbo") -> float:
        """估算成本（美元）"""
        prices = {
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03}
        }
        
        price = prices.get(model, {"input": 0, "output": 0})
        return (tokens / 1000) * price["input"]


class MessageBuilder:
    """消息构建器"""
    
    def __init__(self, system_prompt: str = None):
        self.messages = []
        
        if system_prompt:
            self.add_system(system_prompt)
    
    def add_system(self, content: str) -> 'MessageBuilder':
        """添加系统消息"""
        self.messages.append({"role": "system", "content": content})
        return self
    
    def add_user(self, content: str) -> 'MessageBuilder':
        """添加用户消息"""
        self.messages.append({"role": "user", "content": content})
        return self
    
    def add_assistant(self, content: str) -> 'MessageBuilder':
        """添加助手消息"""
        self.messages.append({"role": "assistant", "content": content})
        return self
    
    def build(self) -> List[Dict]:
        """构建消息列表"""
        return self.messages
    
    def clear(self) -> 'MessageBuilder':
        """清空消息"""
        self.messages = []
        return self


class ResponseParser:
    """响应解析器"""
    
    @staticmethod
    def parse_json(response_text: str) -> dict:
        """解析 JSON 响应"""
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            # 尝试修复常见的 JSON 错误
            import re
            
            # 替换单引号
            fixed = re.sub(r"'([^']*)'", r'"\1"', response_text)
            
            # 移除末尾逗号
            fixed = re.sub(r',\s*}', '}', fixed)
            fixed = re.sub(r',\s*]', ']', fixed)
            
            try:
                return json.loads(fixed)
            except:
                raise ValueError(f"无法解析 JSON: {response_text}") from e
    
    @staticmethod
    def extract_code_blocks(response_text: str, language: str = None) -> List[str]:
        """提取代码块"""
        import re
        
        if language:
            pattern = f'```{language}(.*?)```'
        else:
            pattern = '```(?:\\w+)?(.*?)```'
            
        matches = re.findall(pattern, response_text, re.DOTALL)
        return [match.strip() for match in matches]
    
    @staticmethod
    def extract_list(response_text: str) -> List[str]:
        """提取列表项"""
        import re
        
        # 匹配数字列表或符号列表
        pattern = r'(?:^|\n)\s*(?:\d+\.|[-*•])\s*(.+?)(?=\n|$)'
        matches = re.findall(pattern, response_text)
        return [match.strip() for match in matches]


class PromptOptimizer:
    """提示词优化器"""
    
    @staticmethod
    def shorten(text: str, max_length: int = 1000) -> str:
        """缩短文本"""
        if len(text) <= max_length:
            return text
            
        # 保留重要部分
        paragraphs = text.split('\n')
        result = []
        current_length = 0
        
        for para in paragraphs:
            if current_length + len(para) <= max_length:
                result.append(para)
                current_length += len(para)
            else:
                break
                
        return '\n'.join(result) + '\n...[已截断]'
    
    @staticmethod
    def add_structure(prompt: str) -> str:
        """为提示词添加结构"""
        template = """请按照以下步骤完成任务：

1. 理解问题：仔细阅读并理解用户的需求
2. 分析要求：识别关键信息和约束条件
3. 组织答案：结构化地呈现信息
4. 检查质量：确保答案准确、完整

任务描述：
{prompt}

请开始："""
        
        return template.format(prompt=prompt)
    
    @staticmethod
    def add_examples(prompt: str, examples: List[Dict]) -> str:
        """添加示例到提示词"""
        result = prompt + "\n\n示例：\n"
        
        for i, example in enumerate(examples, 1):
            result += f"\n示例{i}:\n"
            result += f"输入：{example.get('input', '')}\n"
            result += f"输出：{example.get('output', '')}\n"
            
        result += "\n现在请处理以下输入："
        return result


class CostTracker:
    """成本追踪器"""
    
    def __init__(self):
        self.total_cost = 0.0
        self.requests = []
        self.prices = {
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03}
        }
    
    def record(self, model: str, prompt_tokens: int, completion_tokens: int):
        """记录一次请求"""
        price = self.prices.get(model, {"input": 0, "output": 0})
        
        input_cost = (prompt_tokens / 1000) * price["input"]
        output_cost = (completion_tokens / 1000) * price["output"]
        cost = input_cost + output_cost
        
        self.total_cost += cost
        self.requests.append({
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost": cost
        })
    
    def get_total_cost(self) -> float:
        """获取总成本"""
        return self.total_cost
    
    def get_report(self) -> Dict:
        """生成报告"""
        if not self.requests:
            return {"total_requests": 0, "total_cost": 0.0}
            
        return {
            "total_requests": len(self.requests),
            "total_cost": f"${self.total_cost:.4f}",
            "average_cost": f"${self.total_cost/len(self.requests):.4f}",
            "models_used": list(set(r["model"] for r in self.requests))
        }
    
    def reset(self):
        """重置追踪器"""
        self.total_cost = 0.0
        self.requests = []


# 使用示例
if __name__ == "__main__":
    # Token 计数器示例
    counter = TokenCounter()
    text = "这是一个测试文本"
    tokens = counter.count(text)
    print(f"Token 数：{tokens}")
    
    # 消息构建器示例
    builder = MessageBuilder(system_prompt="你是一个助手")
    messages = (builder
        .add_user("你好")
        .add_assistant("你好！有什么可以帮助你的？")
        .add_user("今天天气如何？")
        .build())
    
    print(f"\n消息数：{len(messages)}")
    
    # 成本追踪示例
    tracker = CostTracker()
    tracker.record("gpt-3.5-turbo", 100, 200)
    tracker.record("gpt-4", 500, 1000)
    
    report = tracker.get_report()
    print(f"\n成本报告：{report}")
