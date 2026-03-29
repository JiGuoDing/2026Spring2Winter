"""
OpenAI 库综合示例集合

包含多个实用场景的完整示例代码
"""

from openai import OpenAI, AsyncOpenAI
import asyncio
import json

client = OpenAI()


# ========== 示例 1: 多轮对话机器人 ==========
class ChatBot:
    """支持上下文的聊天机器人"""
    
    def __init__(self, personality="友好助手"):
        self.client = OpenAI()
        self.conversation_history = []
        self.personality = personality
        
        # 系统提示设定角色
        self.system_prompt = {
            "role": "system",
            "content": f"你是一个{personality}。请用简洁、有趣的语言回答用户问题。"
        }
        
    def chat(self, user_input):
        """发送消息并获取回复"""
        # 添加用户消息
        self.conversation_history.append({
            "role": "user",
            "content": user_input
        })
        
        # 构建完整消息
        messages = [self.system_prompt] + self.conversation_history
        
        # 调用 API
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        
        assistant_message = response.choices[0].message.content
        
        # 保存 AI 回复
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })
        
        return assistant_message
    
    def reset(self):
        """重置对话历史"""
        self.conversation_history = []


# ========== 示例 2: 文本摘要生成器 ==========
class TextSummarizer:
    """文本摘要工具"""
    
    def __init__(self):
        self.client = OpenAI()
        
    def summarize(self, text, max_length=100):
        """生成文本摘要"""
        prompt = f"""请为以下文本生成简洁的摘要（不超过{max_length}字）：

{text}

摘要："""
        
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_length * 2,
            temperature=0.3
        )
        
        return response.choices[0].message.content
    
    def extract_key_points(self, text, num_points=3):
        """提取关键点"""
        prompt = f"""请从以下文本中提取{num_points}个关键点，使用列表格式：

{text}

关键点："""
        
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content


# ========== 示例 3: 代码助手 ==========
class CodeAssistant:
    """编程助手"""
    
    def __init__(self):
        self.client = OpenAI()
        
    def explain_code(self, code, language="Python"):
        """解释代码"""
        prompt = f"""请解释以下{language}代码的功能：

```{language}
{code}
```

功能说明："""
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content
    
    def generate_code(self, description, language="Python"):
        """根据描述生成代码"""
        prompt = f"""请编写{language}代码实现以下功能：
{description}

要求：
1. 代码简洁高效
2. 添加必要的注释
3. 包含使用示例

代码："""
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content
    
    def debug_code(self, code, error_message):
        """调试代码"""
        prompt = f"""以下代码出现错误："{error_message}"
请找出问题并提供修复方案：

```python
{code}
```

问题分析："""
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content


# ========== 示例 4: 异步批量处理 ==========
class AsyncBatchProcessor:
    """异步批量处理器"""
    
    def __init__(self):
        self.client = AsyncOpenAI()
        
    async def process_batch(self, texts, batch_size=5):
        """批量处理文本"""
        results = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            tasks = [self.analyze_sentiment(text) for text in batch]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            
            # 避免频率限制
            await asyncio.sleep(0.5)
            
        return results
    
    async def analyze_sentiment(self, text):
        """分析文本情感"""
        prompt = f"请分析以下文本的情感倾向（正面/负面/中性）：\n{text}"
        
        response = await self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content


# ========== 示例 5: 智能翻译器 ==========
class SmartTranslator:
    """智能翻译器"""
    
    def __init__(self):
        self.client = OpenAI()
        
    def translate(self, text, target_language="英语"):
        """翻译文本"""
        prompt = f"""请将以下文本翻译成{target_language}，保持原意和语气：

原文：{text}

译文："""
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        return response.choices[0].message.content
    
    def translate_with_context(self, text, target_language="英语", context=None):
        """带上下文的翻译"""
        if context:
            prompt = f"""上下文：{context}
请根据上下文将以下文本翻译成{target_language}：

原文：{text}

译文："""
        else:
            prompt = f"将以下文本翻译成{target_language}：\n\n原文：{text}\n\n译文："
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content


# ========== 主程序演示 ==========
def main():
    """演示各个示例的使用"""
    
    print("=" * 60)
    print("OpenAI 库综合示例演示")
    print("=" * 60)
    
    # 示例 1: 聊天机器人
    print("\n【示例 1: 聊天机器人】")
    bot = ChatBot(personality="幽默的程序员")
    response = bot.chat("你好，能介绍一下你自己吗？")
    print(f"机器人：{response}")
    
    # 示例 2: 文本摘要
    print("\n【示例 2: 文本摘要】")
    summarizer = TextSummarizer()
    long_text = """
    人工智能是计算机科学的一个分支，它企图了解智能的实质，
    并生产出一种新的能以人类智能相似的方式做出反应的智能机器。
    该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。
    人工智能从诞生以来，理论和技术日益成熟，应用领域也不断扩大。
    """
    summary = summarizer.summarize(long_text, max_length=50)
    print(f"摘要：{summary}")
    
    # 示例 3: 代码助手
    print("\n【示例 3: 代码助手】")
    code_assistant = CodeAssistant()
    code = """
def fibonacci(n):
    if n <= 1:
        return n
    else:
        return fibonacci(n-1) + fibonacci(n-2)
"""
    explanation = code_assistant.explain_code(code)
    print(f"代码解释：{explanation}")
    
    # 示例 4: 异步批处理
    print("\n【示例 4: 异步批处理】")
    processor = AsyncBatchProcessor()
    texts = [
        "这个产品太好用了，强烈推荐！",
        "质量一般，价格偏贵",
        "物流很快，包装完好"
    ]
    
    async def run_batch():
        results = await processor.process_batch(texts)
        for text, result in zip(texts, results):
            print(f"\n文本：{text.strip()}")
            print(f"情感：{result.strip()}")
    
    asyncio.run(run_batch())
    
    # 示例 5: 翻译器
    print("\n【示例 5: 智能翻译】")
    translator = SmartTranslator()
    chinese_text = "春眠不觉晓，处处闻啼鸟"
    translated = translator.translate(chinese_text, target_language="英语")
    print(f"原文：{chinese_text}")
    print(f"译文：{translated}")
    
    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
