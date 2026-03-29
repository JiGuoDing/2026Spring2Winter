# 第六章：常见问题

## 6.1 安装和配置

### Q1: 安装失败怎么办？

**问题**: `pip install openai` 报错

**解决方案**:

```bash
# 1. 升级 pip
python -m pip install --upgrade pip

# 2. 使用国内镜像
pip install openai -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install openai
```

### Q2: API Key 无效

**错误**: `AuthenticationError: Error code: 401`

**检查清单**:
- [ ] API Key 是否正确复制（包含完整的 `sk-` 前缀）
- [ ] 环境变量是否设置成功
- [ ] API Key 是否已激活
- [ ] 账户是否有余额

**调试代码**:
```python
import os
from openai import OpenAI

api_key = os.getenv("OPENAI_API_KEY")
print(f"API Key: {api_key[:10]}...{api_key[-5:]}")
print(f"长度：{len(api_key)}")

client = OpenAI()
```

## 6.2 API 调用问题

### Q3: Rate Limit 错误

**错误**: `RateLimitError: Rate limit reached`

**解决方案**:

```python
# 方法 1: 添加重试逻辑
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def chat_with_retry(messages):
    return client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )

# 方法 2: 降低请求频率
import time

for i in range(10):
    response = client.chat.completions.create(...)
    time.sleep(0.5)  # 每次请求间隔 0.5 秒
```

### Q4: Token 超限

**错误**: `BadRequestError: This model's maximum context length is 4096 tokens`

**解决方案**:

```python
import tiktoken

def truncate_messages(messages, max_tokens=4096):
    """截断消息历史"""
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    
    total_tokens = 0
    truncated_messages = []
    
    for message in reversed(messages):
        tokens = len(encoding.encode(message["content"]))
        
        if total_tokens + tokens <= max_tokens:
            truncated_messages.insert(0, message)
            total_tokens += tokens
        else:
            # 截断当前消息
            remaining = max_tokens - total_tokens
            if remaining > 0:
                encoded = encoding.encode(message["content"])
                truncated_content = encoding.decode(encoded[:remaining])
                truncated_messages.insert(0, {
                    "role": message["role"],
                    "content": truncated_content + "[...]"
                })
            break
    
    return truncated_messages

# 使用
safe_messages = truncate_messages(messages)
response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=safe_messages
)
```

### Q5: 响应格式错误

**问题**: JSON 解析失败

**解决方案**:

```python
import json
from openai import OpenAI

client = OpenAI()

# 方法 1: 使用 JSON 模式
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{
        "role": "user",
        "content": "生成一个包含 name 和 age 的 JSON 对象"
    }],
    response_format={"type": "json_object"}
)

try:
    data = json.loads(response.choices[0].message.content)
except json.JSONDecodeError as e:
    print(f"JSON 解析失败：{e}")
    # 尝试修复常见的 JSON 错误
    import re
    fixed = re.sub(r"'", '"', response.choices[0].message.content)
    data = json.loads(fixed)
```

## 6.3 性能问题

### Q6: 响应速度慢

**优化方案**:

```python
# 1. 使用流式输出
stream = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "写一篇文章"}],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")

# 2. 使用更小的模型
response = client.chat.completions.create(
    model="gpt-3.5-turbo",  # 而不是 gpt-4
    messages=messages
)

# 3. 减少 token 数量
short_prompt = "简要回答：什么是 AI？"  # 而不是"请详细解释..."
```

### Q7: 内存占用高

**问题**: Embedding 大量文本时内存溢出

**解决方案**:

```python
def batch_embeddings(texts, batch_size=20):
    """批量处理，避免内存溢出"""
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input=batch
        )
        
        embeddings = [d.embedding for d in response.data]
        all_embeddings.extend(embeddings)
        
        # 释放内存
        del batch
        del response
        
    return all_embeddings
```

## 6.4 Function Calling 问题

### Q8: 工具调用失败

**问题**: AI 不调用定义的工具

**检查清单**:
- [ ] 工具描述是否清晰
- [ ] 参数定义是否正确
- [ ] 是否在 messages 中包含工具
- [ ] 提示词是否引导使用工具

**改进示例**:

```python
# ❌ 不好的工具定义
tools = [{
    "type": "function",
    "function": {
        "name": "search",
        "description": "搜索信息",  # 太模糊
        "parameters": {"type": "object"}  # 参数不明确
    }
}]

# ✅ 好的工具定义
tools = [{
    "type": "function",
    "function": {
        "name": "search_web",
        "description": "搜索最新的网络信息，适用于新闻、天气、体育等实时信息",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词，例如'北京天气'或'NBA 最新比分'"
                }
            },
            "required": ["query"]  # 明确必需参数
        }
    }
}]

# 在系统提示中说明
system_prompt = """你是一个智能助手。你可以使用以下工具：
- search_web: 当用户询问实时信息、新闻、天气时使用此工具
如果用户的问题需要最新信息，请调用 search_web 工具。
"""
```

### Q9: 工具参数解析错误

**问题**: `json.loads()` 失败

**解决方案**:

```python
import json
import re

def safe_parse_arguments(arguments_str):
    """安全解析工具参数"""
    try:
        # 标准 JSON 解析
        return json.loads(arguments_str)
    except json.JSONDecodeError:
        # 尝试修复常见的 JSON 错误
        
        # 1. 替换单引号为双引号
        fixed = re.sub(r"'([^']*)'", r'"\1"', arguments_str)
        
        # 2. 移除末尾的逗号
        fixed = re.sub(r',\s*}', '}', fixed)
        fixed = re.sub(r',\s*]', ']', fixed)
        
        # 3. 为键添加双引号
        fixed = re.sub(r'([{\[,]\s*)(\w+)(\s*:)', r'\1"\2"\3', fixed)
        
        try:
            return json.loads(fixed)
        except:
            logger.error(f"无法解析参数：{arguments_str}")
            return {}
```

## 6.5 成本和计费

### Q10: 费用过高

**优化建议**:

```python
class CostOptimizer:
    def __init__(self):
        self.client = OpenAI()
        self.total_cost = 0
        
    def choose_model(self, task_complexity):
        """根据任务复杂度选择模型"""
        if task_complexity == "simple":
            return "gpt-3.5-turbo"  # $0.0015/1K tokens
        elif task_complexity == "medium":
            return "gpt-4-turbo"    # $0.01/1K tokens
        else:
            return "gpt-4"          # $0.03/1K tokens
            
    def optimize_prompt(self, prompt):
        """优化提示词长度"""
        # 移除冗余词汇
        words_to_remove = ["请", "麻烦", "能不能", "谢谢"]
        for word in words_to_remove:
            prompt = prompt.replace(word, "")
        return prompt.strip()
        
    def track_usage(self, response):
        """追踪使用情况"""
        usage = response.usage
        # 根据模型计算成本
        cost = (usage.prompt_tokens * 0.0015 + 
                usage.completion_tokens * 0.002) / 1000
        self.total_cost += cost
        return cost

# 使用
optimizer = CostOptimizer()
model = optimizer.choose_model("simple")
prompt = optimizer.optimize_prompt("请问你能帮我吗？")
response = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": prompt}]
)
cost = optimizer.track_usage(response)
print(f"本次成本：${cost:.6f}")
```

## 6.6 生产环境问题

### Q11: 服务不稳定

**建议架构**:

```python
from circuitbreaker import circuit

class ResilientAgent:
    def __init__(self):
        self.client = OpenAI()
        self.fallback_client = None  # 可以配置备用 API
        
    @circuit(failure_threshold=5, recovery_timeout=30)
    def chat(self, messages):
        """带熔断器的聊天"""
        return self.client.chat.completions.create(
            model="gpt-4",
            messages=messages
        )
        
    def chat_with_fallback(self, messages):
        """带降级策略的聊天"""
        try:
            return self.chat(messages)
        except Exception as e:
            logger.error(f"主服务失败：{e}")
            
            # 降级到更简单的模型
            try:
                return self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages
                )
            except Exception as e2:
                logger.error(f"降级也失败：{e2}")
                return "抱歉，服务暂时不可用，请稍后重试"
```

## 6.7 调试技巧

### 启用详细日志

```python
import logging
import httpx

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 创建带调试的客户端
http_client = httpx.Client(
    timeout=30.0,
    transport=httpx.HTTPTransport(
        local_address="0.0.0.0",
        verify=True
    ),
    follow_redirects=True
)

client = OpenAI(http_client=http_client)

# 记录所有请求
def log_request(messages, model):
    logger.debug(f"发送请求到 {model}")
    logger.debug(f"消息：{messages}")
    
response = client.chat.completions.create(
    model="gpt-4",
    messages=messages
)

log_request(messages, "gpt-4")
logger.debug(f"响应：{response.choices[0].message.content}")
```

## 快速诊断脚本

```python
#!/usr/bin/env python3
"""OpenAI 连接诊断脚本"""

import os
import sys
from openai import OpenAI, AuthenticationError

def diagnose():
    print("=== OpenAI 连接诊断 ===\n")
    
    # 1. 检查 API Key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ 错误：未设置 OPENAI_API_KEY 环境变量")
        return False
    print(f"✅ API Key 已设置 ({len(api_key)}字符)")
    
    # 2. 测试连接
    try:
        client = OpenAI()
        response = client.models.list()
        print("✅ 连接成功")
        print(f"   可用模型数：{len(response.data)}")
    except AuthenticationError:
        print("❌ 认证失败：API Key 无效")
        return False
    except Exception as e:
        print(f"❌ 连接失败：{e}")
        return False
    
    # 3. 测试聊天
    try:
        test_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hi"}]
        )
        print("✅ 聊天测试成功")
        print(f"   响应时间：{test_response.usage.total_tokens} tokens")
    except Exception as e:
        print(f"❌ 聊天测试失败：{e}")
        return False
    
    print("\n✅ 所有检查通过！")
    return True

if __name__ == "__main__":
    success = diagnose()
    sys.exit(0 if success else 1)
```

## 获取帮助

### 有用的资源

- **官方文档**: https://platform.openai.com/docs
- **GitHub Issues**: https://github.com/openai/openai-python/issues
- **Stack Overflow**: https://stackoverflow.com/questions/tagged/openai-api
- **Discord 社区**: https://discord.com/invite/openai

### 提问的艺术

遇到问题提问时，请提供：
1. 错误信息的完整截图
2. 最小可复现代码
3. 已尝试的解决方案
4. 环境信息（Python 版本、openai 库版本）

---

**持续更新中...**
