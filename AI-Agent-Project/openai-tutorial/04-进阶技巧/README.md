# 第四章：进阶技巧

## 4.1 异步编程

### 异步客户端使用

```python
import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI()

async def main():
    response = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "你好"}]
    )
    print(response.choices[0].message.content)

asyncio.run(main())
```

### 并发请求

```python
import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI()

async def chat(message):
    response = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": message}]
    )
    return response.choices[0].message.content

async def main():
    # 并发多个请求
    tasks = [
        chat("问题 1"),
        chat("问题 2"),
        chat("问题 3")
    ]
    
    results = await asyncio.gather(*tasks)
    for i, result in enumerate(results, 1):
        print(f"问题{i}的答案：{result}")

asyncio.run(main())
```

### 异步流式

```python
import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI()

async def stream_chat():
    stream = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "讲一个故事"}],
        stream=True
    )
    
    async for chunk in stream:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)

asyncio.run(stream_chat())
```

## 4.2 性能优化

### 批量处理

```python
def batch_process(texts, batch_size=10):
    """批量处理文本"""
    embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input=batch
        )
        embeddings.extend([d.embedding for d in response.data])
        
    return embeddings
```

### 缓存机制

```python
from functools import lru_cache
import hashlib

class CachedClient:
    def __init__(self):
        self.client = OpenAI()
        self.cache = {}
        
    def _get_cache_key(self, model, messages):
        """生成缓存键"""
        key_str = f"{model}:{json.dumps(messages, sort_keys=True)}"
        return hashlib.md5(key_str.encode()).hexdigest()
        
    def chat(self, model, messages, use_cache=True):
        """带缓存的对话"""
        cache_key = self._get_cache_key(model, messages)
        
        if use_cache and cache_key in self.cache:
            print("使用缓存")
            return self.cache[cache_key]
            
        response = self.client.chat.completions.create(
            model=model,
            messages=messages
        )
        
        content = response.choices[0].message.content
        self.cache[cache_key] = content
        
        return content
```

### 连接池优化

```python
import httpx
from openai import OpenAI

# 自定义 HTTP 客户端
http_client = httpx.Client(
    limits=httpx.Limits(
        max_keepalive_connections=10,
        max_connections=50
    ),
    timeout=30.0
)

client = OpenAI(http_client=http_client)
```

## 4.3 重试机制

### 指数退避重试

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def chat_with_retry(messages):
    return client.chat.completions.create(
        model="gpt-4",
        messages=messages
    )
```

### 自定义重试逻辑

```python
import time
from openai import RateLimitError

def chat_with_backoff(messages, max_retries=3):
    """带退避的重试"""
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(
                model="gpt-4",
                messages=messages
            )
        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise
                
            wait_time = (2 ** attempt) + random.random()
            print(f"频率超限，等待{wait_time:.1f}秒后重试...")
            time.sleep(wait_time)
```

## 4.4 Token 优化

### 计算 Token 数量

```python
import tiktoken

def count_tokens(text, model="gpt-3.5-turbo"):
    """计算文本的 token 数"""
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

# 使用示例
text = "这是一段测试文本"
tokens = count_tokens(text)
print(f"Token 数：{tokens}")
```

### 消息长度优化

```python
def truncate_messages(messages, max_tokens=4096):
    """截断消息以适配模型"""
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    
    total_tokens = 0
    truncated = []
    
    for msg in reversed(messages):
        tokens = len(encoding.encode(msg["content"]))
        
        if total_tokens + tokens <= max_tokens:
            truncated.insert(0, msg)
            total_tokens += tokens
        else:
            # 截断当前消息
            remaining = max_tokens - total_tokens
            if remaining > 0:
                encoded = encoding.encode(msg["content"])
                truncated_content = encoding.decode(encoded[:remaining])
                truncated.insert(0, {
                    "role": msg["role"],
                    "content": truncated_content + "...[已截断]"
                })
            break
            
    return truncated
```

## 4.5 结构化输出

### JSON 模式

```python
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{
        "role": "user",
        "content": "生成一个用户信息，包含姓名、年龄、邮箱"
    }],
    response_format={"type": "json_object"}
)

data = json.loads(response.choices[0].message.content)
print(data)
```

### Pydantic 集成

```python
from pydantic import BaseModel
import json

class UserInfo(BaseModel):
    name: str
    age: int
    email: str

prompt = "生成一个用户信息：张三，25 岁，zhangsan@example.com"

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": prompt}],
    response_format={"type": "json_object"}
)

user = UserInfo(**json.loads(response.choices[0].message.content))
print(user.name, user.age, user.email)
```

## 4.6 多模型协作

### 模型链式调用

```python
def multi_step_task(task):
    """多步骤任务处理"""
    # 第一步：GPT-4 规划
    plan_response = client.chat.completions.create(
        model="gpt-4",
        messages=[{
            "role": "user",
            "content": f"请规划如何完成这个任务：{task}"
        }]
    )
    plan = plan_response.choices[0].message.content
    
    # 第二步：GPT-3.5 执行
    exec_response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "你是一个执行助手"},
            {"role": "user", "content": f"根据以下计划执行任务：\n{plan}"}
        ]
    )
    
    return exec_response.choices[0].message.content
```

### 模型投票机制

```python
def ensemble_answer(question, n_models=3):
    """多模型投票回答"""
    answers = []
    
    for _ in range(n_models):
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": question}],
            temperature=0.7
        )
        answers.append(response.choices[0].message.content)
    
    # 使用另一个模型选择最佳答案
    selector_response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": f"""问题：{question}
备选答案：
{chr(10).join([f'{i+1}. {a}' for i, a in enumerate(answers)])}

请选择最准确的答案编号（1-{n_models}）："""}
        ]
    )
    
    best_idx = int(selector_response.choices[0].message.content.strip()) - 1
    return answers[best_idx]
```

## 4.7 监控和日志

### 请求日志

```python
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LoggedClient:
    def __init__(self):
        self.client = OpenAI()
        
    def chat(self, model, messages, **kwargs):
        start_time = datetime.now()
        
        logger.info(f"请求开始：{model}")
        logger.info(f"消息数：{len(messages)}")
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            usage = response.usage
            
            logger.info(f"请求完成，耗时：{duration:.2f}s")
            logger.info(f"Token 使用：输入={usage.prompt_tokens}, "
                       f"输出={usage.completion_tokens}, "
                       f"总计={usage.total_tokens}")
            
            return response
            
        except Exception as e:
            logger.error(f"请求失败：{e}")
            raise
```

### 成本追踪

```python
class CostTracker:
    PRICES = {
        "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03}
    }
    
    def __init__(self):
        self.total_cost = 0
        self.requests = []
        
    def track(self, model, usage):
        """记录使用并计算成本"""
        price = self.PRICES.get(model, {"input": 0, "output": 0})
        
        input_cost = (usage.prompt_tokens / 1000) * price["input"]
        output_cost = (usage.completion_tokens / 1000) * price["output"]
        cost = input_cost + output_cost
        
        self.total_cost += cost
        self.requests.append({
            "model": model,
            "cost": cost,
            "timestamp": datetime.now()
        })
        
        return cost
        
    def get_report(self):
        """生成报告"""
        return {
            "总请求数": len(self.requests),
            "总成本": f"${self.total_cost:.4f}",
            "平均成本": f"${self.total_cost/len(self.requests):.4f}" 
                       if self.requests else "$0.0000"
        }
```

## 练习题

1. 实现异步版本的 Agent
2. 添加缓存机制优化性能
3. 实现 Token 计数器
4. 创建成本追踪系统

## 下一步

继续学习 [最佳实践](../05-最佳实践/README.md)
