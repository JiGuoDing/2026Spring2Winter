# 第五章：最佳实践

## 5.1 代码组织

### 项目结构建议

```
my-agent-project/
├── config/              # 配置文件
│   ├── __init__.py
│   └── settings.py     # 配置和常量
├── agents/             # Agent 实现
│   ├── __init__.py
│   ├── base.py        # 基础 Agent 类
│   └── assistant.py   # 助手 Agent
├── tools/              # 工具定义
│   ├── __init__.py
│   ├── web_search.py  # 搜索工具
│   └── calculator.py  # 计算工具
├── memory/             # 记忆系统
│   ├── __init__.py
│   ├── short_term.py  # 短期记忆
│   └── long_term.py   # 长期记忆
├── utils/              # 工具函数
│   ├── __init__.py
│   ├── logger.py      # 日志
│   └── helpers.py     # 辅助函数
├── tests/              # 测试
│   ├── test_agents.py
│   └── test_tools.py
├── .env                # 环境变量
├── requirements.txt    # 依赖
└── main.py            # 入口文件
```

### 模块化设计

```python
# agents/base.py
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.client = OpenAI()
        
    @abstractmethod
    def chat(self, message: str) -> str:
        pass
        
    @abstractmethod
    def run(self):
        pass

# agents/assistant.py
from .base import BaseAgent

class AssistantAgent(BaseAgent):
    def __init__(self, name: str = "助手"):
        super().__init__(name)
        self.tools = []
        
    def chat(self, message: str) -> str:
        # 实现具体逻辑
        pass
        
    def run(self):
        # 运行逻辑
        pass
```

## 5.2 错误处理

### 完整的错误处理策略

```python
from openai import (
    OpenAIError,
    APIError,
    APIConnectionError,
    RateLimitError,
    AuthenticationError,
    BadRequestError
)

def safe_chat(messages, model="gpt-4"):
    """安全的聊天调用"""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages
        )
        return response.choices[0].message.content
        
    except AuthenticationError:
        logger.error("API Key 认证失败")
        return "抱歉，身份验证失败"
        
    except RateLimitError:
        logger.warning("请求频率超限")
        time.sleep(2 ** retry_count)
        return safe_chat(messages, model)
        
    except APIConnectionError:
        logger.error("API 连接失败")
        return "抱歉，网络连接问题"
        
    except BadRequestError as e:
        logger.error(f"请求参数错误：{e}")
        return "抱歉，请求格式不正确"
        
    except APIError as e:
        logger.error(f"API 错误：{e.status_code} - {e.message}")
        return f"服务器错误：{e.status_code}"
        
    except Exception as e:
        logger.exception(f"未知错误：{e}")
        return "抱歉，发生了未知错误"
```

### 重试装饰器

```python
from functools import wraps
import time
import random

def retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0):
    """带退避的重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                    
                except (RateLimitError, APIConnectionError) as e:
                    last_exception = e
                    
                    if attempt == max_retries - 1:
                        break
                        
                    # 指数退避 + 抖动
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = random.uniform(0, delay * 0.1)
                    
                    logger.warning(
                        f"第{attempt+1}次尝试失败，"
                        f"等待{delay+jitter:.2f}秒后重试"
                    )
                    time.sleep(delay + jitter)
                    
                except Exception as e:
                    logger.exception(f"非重试错误：{e}")
                    raise
                    
            raise last_exception
            
        return wrapper
    return decorator

@retry_with_backoff(max_retries=3)
def chat_with_retry(messages):
    return client.chat.completions.create(
        model="gpt-4",
        messages=messages
    )
```

## 5.3 安全性

### API Key 管理

```python
# .env 文件
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://...
SECRET_KEY=your-secret-key

# config/settings.py
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    @property
    def is_production(self):
        return os.getenv("ENVIRONMENT") == "production"
        
settings = Settings()
```

### 输入验证

```python
import re

def validate_input(text: str, max_length: int = 4096) -> bool:
    """验证用户输入"""
    if not text or not text.strip():
        return False
        
    if len(text) > max_length:
        return False
        
    # 检查恶意模式
    dangerous_patterns = [
        r'<script.*?>',  # XSS
        r'SELECT.*FROM',  # SQL 注入
        r'\.\./\.\.',     # 路径遍历
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            logger.warning(f"检测到潜在攻击：{text[:100]}")
            return False
            
    return True

def sanitize_input(text: str) -> str:
    """清理用户输入"""
    # 移除控制字符
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
    # 限制长度
    return text[:4096]
```

### 输出过滤

```python
def filter_output(text: str) -> str:
    """过滤 AI 输出"""
    # 移除潜在的敏感信息
    sensitive_patterns = [
        r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',  # 信用卡号
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # 邮箱
        r'\b\d{11}\b',  # 手机号
    ]
    
    for pattern in sensitive_patterns:
        text = re.sub(pattern, '[已过滤]', text)
        
    return text
```

## 5.4 性能优化

### 连接池配置

```python
import httpx
from openai import OpenAI

# 创建优化的 HTTP 客户端
http_client = httpx.Client(
    limits=httpx.Limits(
        max_keepalive_connections=20,
        max_connections=100
    ),
    timeout=httpx.Timeout(30.0, connect=10.0),
    headers={
        "User-Agent": "MyAgent/1.0"
    }
)

client = OpenAI(http_client=http_client)
```

### 批量操作

```python
async def batch_embed_texts(texts: list[str], batch_size: int = 20):
    """批量生成嵌入"""
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        response = await client.embeddings.create(
            model="text-embedding-ada-002",
            input=batch
        )
        
        embeddings = [d.embedding for d in response.data]
        all_embeddings.extend(embeddings)
        
        # 避免频率限制
        await asyncio.sleep(0.1)
        
    return all_embeddings
```

## 5.5 测试

### 单元测试

```python
import pytest
from unittest.mock import Mock, patch
from agents.assistant import AssistantAgent

@pytest.fixture
def agent():
    return AssistantAgent(name="测试助手")

def test_agent_initialization(agent):
    assert agent.name == "测试助手"
    assert agent.client is not None

@patch('openai.OpenAI')
def test_chat(mock_openai, agent):
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="你好"))]
    mock_openai.return_value.chat.completions.create.return_value = mock_response
    
    response = agent.chat("你好")
    
    assert response == "你好"
    mock_openai.return_value.chat.completions.create.assert_called_once()

def test_tool_registration(agent):
    @tool(description="测试工具", parameters={"type": "object"})
    def test_tool():
        return "test"
    
    agent.tool_manager.register(test_tool)
    assert "test_tool" in agent.tool_manager.tools
```

### 集成测试

```python
@pytest.mark.integration
class TestAgentIntegration:
    @pytest.mark.asyncio
    async def test_conversation_flow(self):
        agent = AssistantAgent()
        
        # 多轮对话测试
        responses = []
        for question in ["你好", "今天天气如何", "再见"]:
            response = agent.chat(question)
            responses.append(response)
            assert response is not None
            assert len(response) > 0
            
    def test_tool_execution(self):
        agent = AssistantAgent()
        agent.register_tools()
        
        result = agent.tool_manager.execute(
            "calculate",
            {"expression": "2+2*3"}
        )
        assert "8" in result
```

## 5.6 文档

### API 文档示例

```python
class AssistantAgent:
    """
    智能助手 Agent
    
    Attributes:
        name (str): 助手名称
        client (OpenAI): OpenAI 客户端
        tools (list): 可用工具列表
        
    Example:
        >>> agent = AssistantAgent(name="小智")
        >>> agent.register_tools()
        >>> response = agent.chat("你好")
        >>> print(response)
    """
    
    def chat(self, message: str) -> str:
        """
        处理用户消息并返回回复
        
        Args:
            message (str): 用户输入消息
            
        Returns:
            str: AI 回复内容
            
        Raises:
            APIError: 当 API 调用失败时
            ValueError: 当输入无效时
            
        Example:
            >>> response = agent.chat("北京天气怎么样？")
            >>> print(response)
            "北京今天晴朗，温度 25°C"
        """
        pass
```

## 5.7 监控和告警

### Prometheus 指标

```python
from prometheus_client import Counter, Histogram, Gauge

# 定义指标
REQUEST_COUNT = Counter(
    'openai_requests_total',
    'Total OpenAI requests',
    ['model', 'endpoint']
)

REQUEST_DURATION = Histogram(
    'openai_request_duration_seconds',
    'OpenAI request duration',
    ['model', 'endpoint']
)

TOKEN_USAGE = Counter(
    'openai_tokens_total',
    'Total tokens used',
    ['model', 'type']  # type: prompt or completion
)

ERROR_COUNT = Counter(
    'openai_errors_total',
    'Total OpenAI errors',
    ['error_type']
)

# 使用指标
@REQUEST_DURATION.labels(model='gpt-4', endpoint='chat').time()
def tracked_chat(messages):
    REQUEST_COUNT.labels(model='gpt-4', endpoint='chat').inc()
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages
        )
        
        TOKEN_USAGE.labels(
            model='gpt-4',
            type='prompt'
        ).inc(response.usage.prompt_tokens)
        
        TOKEN_USAGE.labels(
            model='gpt-4',
            type='completion'
        ).inc(response.usage.completion_tokens)
        
        return response
        
    except Exception as e:
        ERROR_COUNT.labels(error_type=type(e).__name__).inc()
        raise
```

## 检查清单

### 上线前检查

- [ ] API Key 安全存储
- [ ] 错误处理完善
- [ ] 重试机制实现
- [ ] 输入验证添加
- [ ] 输出过滤配置
- [ ] 日志记录完整
- [ ] 监控指标设置
- [ ] 性能测试通过
- [ ] 文档完善

### 日常运维

- [ ] 监控 API 使用量
- [ ] 检查错误率
- [ ] 审查 Token 消耗
- [ ] 更新依赖包
- [ ] 备份重要数据
- [ ] 轮换 API Key

## 下一步

查看 [常见问题](../06-常见问题/README.md)
