# Agent 基础框架与能力抽象

**角色定位**

你是 AI Agent 系统架构方向的资深专家，熟悉 LangChain、Workflow、Agent、Tool、Skill、MCP、A2A、路由、安全机制和规划执行闭环。

**使用场景**

我正在准备 Agent 基础框架、能力抽象和系统架构相关的技术面试。本文件聚焦 Agent 的基本概念、核心组件、能力封装和架构分层。

**回答目标**

请帮助我建立 Agent 系统的整体知识框架，明确不同概念之间的边界，并能在面试中讲清楚 Agent 如何从简单工具调用演进到复杂任务执行系统。

**回答要求**

1. 先给出核心概念的准确定义，并明确它解决的问题。
2. 对 Chain、Agent、Workflow、Tool、Skill、MCP、A2A 等概念，要说明定位、边界、联系和典型场景。
3. 对系统架构类问题，要说明输入、状态、工具、执行器、记忆、路由和安全边界。
4. 对面试高频对比题，要使用表格或分点方式明确差异。
5. 回答要兼顾抽象架构和实际工程，不要只停留在框架名词。
6. 最后补充知识扩展，并给出一段面试中可以直接复述的总结。

**输出格式**

建议使用“定义 → 背景问题 → 架构拆解 → 核心组件 → 对比分析 → 工程实践 → 面试回答”的结构。

**风格约束**

- 使用中文和 Markdown。
- 术语首次出现时尽量给出英文原名。
- 如果出现括号，请使用英文括号 ()，不要使用中文括号。
- 回答要强调概念边界，避免把 Agent、Workflow 和 Tool 混用。

---



## 2.1 LangChain 的核心组件有哪些？Langchain 的核心架构是什么样的？

LangChain 是一个用于构建基于 LLM 应用等开源框架。其核心思想是将 LLM 与外部数据源、计算资源进行连接，通过模块化、可组合的方式构建复杂的 AI 应用。

> LangChain 的设计哲学：将各个独立的功能模块串联起来，形成处理管道 (Pipeline)。

### 包结构

```plaintext
langchain 生态系统
├── langchain-core        # 核心抽象层 (接口定义、基类、LCEL)
├── langchain             # 主包 (Chains, Agents, Memory 等高层组件)
├── langchain-community   # 社区集成 (第三方工具、模型、向量库等)
└── langchain-experimental # 实验性功能
```

### 核心组件详解

#### Models (模型层) —— 与 LLM 交互的入口

LangChain 将模型抽象为三类

| 类型            | 说明                     | 示例                                      |
| --------------- | ------------------------ | ----------------------------------------- |
| LLM             | 文本输入 -> 文本输出     | `OpenAI, HF`                              |
| Chat Model      | 消息列表输入 -> 消息输出 | `ChatOpenAI, ChatAnthropic`               |
| Embedding Model | 文本 -> 向量             | `OpenAIEmbeddings, HuggingFaceEmbeddings` |

```python
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# Chat Model: 接收消息列表, 返回 AIMessage
chat_model = ChatOpenAI(
    model="gpt-4o",
    temperature=0.7,    # 控制随机性, 0=确定性最强
    max_tokens=1024
)

# Embedding Model: 将文本转为向量, 用于语义搜索
embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
```

#### Prompts (提示层) —— 结构化输入管理

Prompt 模板负责将动态变量注入到标准化的提示结构中

```python
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    FewShotPromptTemplate,
    PromptTemplate
)

# --- 基础 ChatPromptTemplate ---
# 使用 {variable} 语法定义占位符
chat_prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个专业的{domain}领域专家, 请用简洁专业的语言回答问题。"),
    ("human", "请解释一下: {question}")
])

# 格式化: 将变量填入模板
formatted = chat_prompt.format_messages(
    domain="机器学习",
    question="什么是梯度消失问题？"
)
# 输出: [SystemMessage(...), HumanMessage(...)]

# --- FewShotPromptTemplate: 提供少量示例引导模型输出格式 ---
examples = [
    {"input": "happy", "output": "sad"},
    {"input": "tall",  "output": "short"},
]
few_shot_prompt = FewShotPromptTemplate(
    examples=examples,
    example_prompt=PromptTemplate(
        input_variables=["input", "output"],
        template="Input: {input}\nOutput: {output}"
    ),
    prefix="Give the antonym of every input word.",
    suffix="Input: {adjective}\nOutput:",
    input_variables=["adjective"]
)
```

#### Chains (链) —— 组件的顺序组合

Chain 是 LangChain 的核心概念，将多个组件串联成一个处理流程。

现代方式：LCEL (LangChain Expression Language)

LCEL 是 LangChain 推荐的链式组合方式，使用 `|` 管道运算符：

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 定义各组件
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个代码专家"),
    ("human", "用 {language} 实现 {task}")
])
model = ChatOpenAI(model="gpt-4o")
parser = StrOutputParser()  # 将 AIMessage 转为纯字符串

# LCEL 管道组合: prompt -> model -> parser
# 数据流: 输入字典 -> 格式化消息 -> LLM响应 -> 字符串
chain = prompt | model | parser

# 调用链
result = chain.invoke({
    "language": "Python",
    "task": "实现快速排序"
})

# 流式输出 (LCEL 原生支持)
for chunk in chain.stream({"language": "Python", "task": "实现快速排序"}):
    print(chunk, end="", flush=True)

# 批量处理
results = chain.batch([
    {"language": "Python", "task": "冒泡排序"},
    {"language": "Java",   "task": "二分查找"},
])
```

顺序链示例 (Sequential Chain)

```python
from langchain_core.runnables import RunnablePassthrough

# 链1: 生成大纲
outline_chain = (
    ChatPromptTemplate.from_template("为主题'{topic}'生成一个文章大纲") 
    | model 
    | StrOutputParser()
)

# 链2: 根据大纲扩写 (使用 RunnablePassthrough 传递上游数据)
article_chain = (
    ChatPromptTemplate.from_template("根据以下大纲写一篇完整文章:\n{outline}") 
    | model 
    | StrOutputParser()
)

# 将两个链组合: 第一个链的输出作为第二个链的输入
full_chain = (
    {"outline": outline_chain}   # 先运行 outline_chain, 结果存入 "outline" key
    | article_chain
)

result = full_chain.invoke({"topic": "大模型的发展历程"})
```

#### Memory (记忆) —— 对话上下文管理

Memory 组件负责在多轮对话中保存和读取历史信息，解决 LLM 无状态的问题。

```python
from langchain.memory import (
    ConversationBufferMemory,       # 保存完整对话历史
    ConversationBufferWindowMemory, # 只保存最近 K 轮
    ConversationSummaryMemory,      # 将历史总结压缩 (适合长对话)
)
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

# --- 现代 LCEL 方式管理 Memory ---
# 用字典模拟多用户会话存储
session_store = {}

def get_session_history(session_id: str):
    """根据 session_id 获取对话历史 (支持多用户)"""
    if session_id not in session_store:
        session_store[session_id] = InMemoryChatMessageHistory()
    return session_store[session_id]

# 构建带记忆的链
prompt_with_history = ChatPromptTemplate.from_messages([
    ("system", "你是一个助手"),
    ("placeholder", "{chat_history}"),  # 历史消息插入位置
    ("human", "{input}")
])

chain_with_memory = RunnableWithMessageHistory(
    prompt_with_history | model | StrOutputParser(),
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history"
)

# 第一轮
chain_with_memory.invoke(
    {"input": "我叫小明"},
    config={"configurable": {"session_id": "user_001"}}
)

# 第二轮: 模型能记住上一轮的内容
chain_with_memory.invoke(
    {"input": "我叫什么名字？"},
    config={"configurable": {"session_id": "user_001"}}
)
# 输出: "你叫小明。"
```

不同 Memory 类型对比：

| Memory 类型          | 存储内容   | 适用场景 | Token 消耗    |
| -------------------- | ---------- | -------- | ------------- |
| `BufferMemory`       | 完整历史   | 短对话   | 高 (线性增长) |
| `BufferWindowMemory` | 最近 K 轮  | 中等对话 | 固定上限      |
| `SummaryMemory`      | 历史摘要   | 长对话   | 低 (压缩后)   |
| `VectorStoreMemory`  | 向量化历史 | 超长对话 | 按需检索      |

#### Indexes & Retrievers (索引与检索) —— RAG 的核心

这是构建 RAG 应用的关键组件链路：

```plaintext
Document Loaders → Text Splitters → Embedding → Vector Store → Retriever
    (加载文档)       (切分文本)        (向量化)      (存储)         (检索)
```

```python
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.runnables import RunnablePassthrough

# Step 1: 加载文档
loader = PyPDFLoader("document.pdf")
docs = loader.load()  # 返回 List[Document]

# Step 2: 切分文本
# RecursiveCharacterTextSplitter 按段落->句子->词语层级切分, 保证语义完整
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,       # 每个块最大字符数
    chunk_overlap=50,     # 块之间的重叠字符数 (避免语义断裂)
    separators=["\n\n", "\n", "。", " "]  # 优先按段落切分
)
chunks = splitter.split_documents(docs)

# Step 3 & 4: 向量化 + 存入向量数据库
vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=OpenAIEmbeddings()
)

# Step 5: 创建检索器
retriever = vectorstore.as_retriever(
    search_type="mmr",   # MMR (最大边际相关性): 兼顾相关性和多样性
    search_kwargs={"k": 4, "fetch_k": 20}
)

# 构建完整 RAG Chain
rag_prompt = ChatPromptTemplate.from_template("""
根据以下上下文回答问题。如果上下文中没有答案，请说"我不知道"。

上下文: {context}

问题: {question}
""")

def format_docs(docs):
    """将检索到的文档列表拼接为字符串"""
    return "\n\n".join(doc.page_content for doc in docs)

rag_chain = (
    {
        "context": retriever | format_docs,  # 检索 -> 格式化
        "question": RunnablePassthrough()    # 问题直接传递
    }
    | rag_prompt
    | model
    | StrOutputParser()
)

answer = rag_chain.invoke("文档中提到了哪些核心概念？")
```

#### Agents (代理) —— 自主决策与工具使用

Agent 是 LangChain 中最强大的组件，让 LLM 能够自主决定调用哪些工具来完成任务

```plaintext
用户输入 → Agent (LLM推理) → 决策使用哪个 Tool → Tool 执行 → 结果返回 → 继续推理 → 最终输出
              ↑_____________________________|  (循环直到任务完成)
```

```python
from langchain_core.tools import tool
from langchain.agents import create_tool_calling_agent, AgentExecutor

# 定义工具 (Tools)
@tool
def search_web(query: str) -> str:
    """搜索互联网获取实时信息。当需要最新资讯时使用此工具。"""
    # 实际中接入 SerpAPI / Tavily 等
    return f"搜索结果: 关于'{query}'的最新信息..."

@tool
def calculator(expression: str) -> str:
    """执行数学计算。输入数学表达式字符串, 返回计算结果。"""
    try:
        result = eval(expression)  # 生产环境中应使用安全的计算器
        return str(result)
    except Exception as e:
        return f"计算错误: {e}"

# 工具列表
tools = [search_web, calculator]

# Agent Prompt (需要包含 agent_scratchpad 用于记录推理过程)
agent_prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个有用的助手, 可以使用工具来回答问题。"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}")  # LLM 的推理轨迹存放处
])

# 创建 Agent (使用 Tool Calling 模式, 依赖模型的 function calling 能力)
agent = create_tool_calling_agent(
    llm=ChatOpenAI(model="gpt-4o"),
    tools=tools,
    prompt=agent_prompt
)

# AgentExecutor: 负责循环执行 agent 直到完成任务
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,       # 打印推理过程
    max_iterations=5,   # 最大循环次数, 防止无限循环
    handle_parsing_errors=True
)

result = agent_executor.invoke({
    "input": "现在比特币的价格是多少？然后计算如果涨了 15% 会是多少？"
})
# Agent 会自动: 1) 调用 search_web 查价格  2) 调用 calculator 计算涨幅
```

#### Output Parsers (输出解释器) —— 结构化输出

将 LLM 的自然语言输出转换为结构化数据：

```python
from langchain_core.output_parsers import (
    StrOutputParser,       # 纯字符串
    JsonOutputParser,      # JSON 格式
    PydanticOutputParser,  # Pydantic 模型
)
from pydantic import BaseModel, Field
from typing import List

# 定义期望的输出结构
class MovieReview(BaseModel):
    title: str = Field(description="电影标题")
    rating: float = Field(description="评分 (0-10)")
    pros: List[str] = Field(description="优点列表")
    cons: List[str] = Field(description="缺点列表")

# Pydantic 解析器: 确保输出符合数据模型
parser = PydanticOutputParser(pydantic_object=MovieReview)

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个电影评论家。\n{format_instructions}"),
    ("human", "评价电影: {movie_name}")
]).partial(format_instructions=parser.get_format_instructions())

chain = prompt | model | parser

# 输出直接是 MovieReview 对象, 而不是字符串
review: MovieReview = chain.invoke({"movie_name": "星际穿越"})
print(review.rating)  # 9.2
print(review.pros)    # ["视觉效果震撼", "科学考据严谨", ...]
```

### 核心架构总揽

```plaintext
┌─────────────────────────────────────────────────────────────────┐
│                        用户应用层 (Application)                   │
│              (RAG App / Chatbot / Agent System / ...)           │
└──────────────────────────────┬──────────────────────────────────┘
                               │  LCEL 管道组合 (| 运算符)
┌──────────────────────────────▼──────────────────────────────────┐
│                     Chain / Agent 编排层                         │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐    │
│   │ Memory  │  │Retriever│  │  Tools  │  │  Output Parser  │    │
│   └────┬────┘  └────┬────┘  └────┬────┘  └─────────┬───────┘    │
└────────┼────────────┼────────────┼─────────────────┼────────────┘
         │            │            │                 │
┌────────▼────────────▼────────────▼─────────────────▼───────────┐
│                      核心抽象层 (langchain-core)                 │
│              Runnable Protocol / LCEL / Base Classes           │
└──────────────────────────────┬─────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                      模型交互层 (Models)                          │
│        LLM / Chat Model / Embedding Model                       │
└─────────────────────────────────────────────────────────────────┘
```

#### Runnable Protocol —— 统一接口的核心设计

LangChain 中所有组件都实现了 `Runnable` 借口，这使得他们可以被统一调用和组合：

```python
# 所有 Runnable 组件都支持以下接口:
component.invoke(input)              # 同步调用
await component.ainvoke(input)       # 异步调用
component.stream(input)              # 流式输出
await component.astream(input)       # 异步流式
component.batch([input1, input2])    # 批量处理
await component.abatch([...])        # 异步批量

# 正是因为统一的 Runnable 接口, | 运算符才能任意组合组件:
# prompt (Runnable) | model (Runnable) | parser (Runnable)
```

### 完整 RAG 应用实例 (综合所有组件)

```python
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory

# ---- 1. 构建知识库 ----
loader = WebBaseLoader("https://example.com/docs")
docs = loader.load()
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(docs)

vectorstore = Chroma.from_documents(chunks, OpenAIEmbeddings())
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# ---- 2. 定义提示模板 ----
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个知识库问答助手。根据以下上下文回答用户的历史问题:\n上下文: {context}"),
    ("placeholder", "{chat_history}"),
    ("human", "{input}")
])

# ---- 3. 构建核心链 ----
model = ChatOpenAI(model="gpt-4o")

rag_chain = (
    RunnablePassthrough.assign(
        # 用当前问题检索相关文档并格式化
        context=lambda x: "\n".join(
            doc.page_content for doc in retriever.invoke(x["input"])
        )
    )
    | prompt
    | model
    | StrOutputParser()
)

# ---- 4. 添加记忆 ----
session_store = {}

final_chain = RunnableWithMessageHistory(
    rag_chain,
    lambda sid: session_store.setdefault(sid, InMemoryChatMessageHistory()),
    input_messages_key="input",
    history_messages_key="chat_history"
)

# ---- 5. 多轮对话 ----
config = {"configurable": {"session_id": "session_001"}}

answer1 = final_chain.invoke({"input": "这个框架的主要特点是什么？"}, config=config)
answer2 = final_chain.invoke({"input": "刚才你提到的第一个特点能详细说说吗？"}, config=config)
# 第二个问题中, "刚才你提到的" 能被正确理解, 因为有 Memory
```

## 2.2 解释LangChain框架中的Chain和Agent概念，并举例说明各自的应用场景

> Chain 和 Agent 是 LangChain 中两种核心的任务编排抽象，它们解决的问题层次不同。
> 
> Chain 本质上是一条固定的执行流水线，将 Prompt、LLM、输出解析器等组件串联起来，形成一个确定性的数据流。它的执行路径在设计时就已固定，适合流程清晰、可预测的任务。现代 LangChain 推荐使用 LCEL (LangChain Expression Language) 通过管道符 | 组合各组件构建 Chain。典型场景包括 RAG 问答系统、文档摘要处理、格式化数据提取等，这类任务的共同特点是步骤明确、不需要动态调整。
> 
> Agent 则是更高级的抽象，它以 LLM 作为核心决策引擎，赋予模型感知环境、调用工具、迭代推理的能力。Agent 采用 ReAct (Reasoning + Acting) 框架，在 Observation→Thought→Action 的循环中动态决定下一步行动，直到完成目标。Agent 的执行路径是运行时由 LLM 动态决定的，因此适合处理开放性强、需要多工具协作的复杂任务，例如智能搜索助手、自动化数据分析、代码调试等。
> 
> 两者的本质区别在于控制权归属: Chain 的控制权在开发者手中 (硬编码流程)，而 Agent 的控制权交给了 LLM (动态决策)。在实际工程中，两者往往结合使用，比如用 Agent 作为顶层决策器，Agent 调用的每个工具内部可以是一个 Chain，这样既保证了灵活性，又在局部保持了可控性。此外，随着 LangGraph 的出现，基于图结构的 Agent 构建方式已成为处理复杂多步任务的主流选择。

### 核心概念

#### Chain

Chain 是 LangChain 中最基础的组件之一，其核心思想是将 **多个组件串联起来，形成一条固定的、预定义的执行流水线 (Pipeline)。**

> 一句话理解: Chain 是一种 "固定剧本"，执行路径在设计时就已经确定，输入经过一系列预设步骤后得到输出。

Chain 的特点：

- **确定性 (Deterministic)** : 执行路径固定，不会根据中间结果动态调整
- **可组合性 (Composability)** : 多个 Chain 可以嵌套组合
- **可预测性 (Predictability)** : 用户清楚地知道每一步在做什么
- **输入输出明确** : 每个 Chain 有明确的输入变量和输出变量

#### Agent

Agent (智能体) 是一种更高级的抽象，其核心是让  **LLM 作为"决策引擎"** ，根据当前状态动态选择下一步行动，而不是遵循固定流程。

> 一句话理解: Agent 是一种 "即兴发挥"，它能够感知环境、调用工具、推理决策，并根据反馈动态调整行为，直到完成目标。

Agent 的特点：

- **动态性 (Dynamic)** : 执行路径由 LLM 在运行时决定
- **工具调用 (Tool Use)** : 能够选择并调用外部工具 (搜索、计算器、数据库等)
- **循环推理 (Iterative Reasoning)** : 采用 Observe → Think → Act 循环
- **不确定性** : 执行步骤数和路径不固定

### 深入解析

#### Chain 的底层原理

Chain 的核心接口是 `Runnable` (LangChain v0.1+ 后的新接口，基于 LCEL)，其本质是一个函数组合：

```plaintext
Chain(input) = f_n(...f_2(f_1(input)))
```

常见的 Chain 类型：

| Chain 类型        | 功能描述                                      |
| ----------------- | --------------------------------------------- |
| LLMChain          | 最基础，Prompt -> LLM -> Output               |
| SequentialChain   | 多个 Chain 顺序执行，前一个输出作为后一个输入 |
| RouterChain       | 根据输入路由到不同的子 Chain                  |
| RetrievalQAChain  | 结合向量检索的问答 Chain                      |
| ConversationChain | 带记忆的对话 Chain                            |

#### Agent 的底层原理

Agent 的核心是 ReAct(Reasoning + Acting) 框架：

```plaintext
Observation → Thought → Action → Observation → ... → Final Answer
```

Agent 的核心组件：

```plaintext
┌─────────────────────────────────────────┐
│                  Agent                  │
│                                         │
│  ┌──────────┐    ┌──────────────────┐   │
│  │  LLM     │───▶│  Action Decision │   │
│  │(决策引擎) │    │  (选择工具/参数)   │   │
│  └──────────┘    └──────────────────┘   │
│        ▲                  │             │
│        │                  ▼             │
│  ┌──────────┐    ┌──────────────────┐   │
│  │  Memory  │    │   Tool Executor  │   │
│  │ (记忆)    │    │   (执行工具)      │   │
│  └──────────┘    └──────────────────┘   │
│                           │             │
│                           ▼             │
│                  ┌──────────────────┐   │
│                  │   Observation    │   │
│                  │  (观察工具结果)    │   │
│                  └──────────────────┘   │
└─────────────────────────────────────────┘
```

常见 Agent 类型：

| Agent 类型             | 特点                                        |
| ---------------------- | ------------------------------------------- |
| ReAct Agent            | 最经典、交替推理和行动                      |
| OpenAI Function Agent  | 利用 OpenAI Function Calling 实现工具调用   |
| OpenAI Tools Agent     | Function Calling 的升级版，支持并行工具调用 |
| Self-Ask with Search   | 通过自问自答分解复杂问题                    |
| Plan-and-Execute Agent | 先规划所有步骤再执行，适合长任务            |

#### Chain 和 Agent 的本质区别

```plaintext
          Chain                         Agent
    ┌─────────────┐               ┌─────────────┐
    │  固定流程    │               │  动态决策   │
    │  Step 1     │               │    LLM      │
    │     ↓       │               │   ↙  ↘      │
    │  Step 2     │               │ Tool A  ?   │
    │     ↓       │               │   ↓   ↘     │
    │  Step 3     │               │ Result  Tool B│
    │     ↓       │               │   ↓         │
    │  Output     │               │  Answer     │
    └─────────────┘               └─────────────┘
    可预测，效率高                灵活，适应复杂任务
```

#### Chain 应用场景

**场景** : 文章摘要生成系统 (固定流程：读取文章 → 生成摘要 → 翻译成中文)

**适合用 Chain 的情况** :

- 任务流程固定、步骤明确
- 对可控性和可预测性要求高
- 生产环境中需要稳定运行
- 例如: 文档处理流水线、RAG 问答系统、固定格式的报告生成

#### Agent 应用场景

**场景** : 智能数据分析助手 (需要根据问题动态决定：是查数据库、还是搜索网络、还是执行代码)

**适合用 Agent 的情况** :

- 任务需要多步推理，且步骤不确定
- 需要调用多种外部工具
- 任务目标明确但实现路径灵活
- 例如: 智能客服、代码助手、自动化研究助手

### 代码示例

#### Chain 示例 (基于 LCEL)

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ============================================================
# 示例: 一个简单的文章摘要 + 翻译 Chain (SequentialChain)
# 流程固定: 原文 -> 英文摘要 -> 中文翻译
# ============================================================

llm = ChatOpenAI(model="gpt-4o", temperature=0)

# --- Step 1: 定义摘要 Prompt ---
summary_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert at summarizing articles concisely."),
    ("human", "Please summarize the following article in 3 sentences:\n\n{article}")
])

# --- Step 2: 定义翻译 Prompt ---
translate_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a professional translator. Translate the given text to Chinese."),
    ("human", "Translate this to Chinese:\n\n{summary}")
])

# --- Step 3: 定义输出解析器 ---
output_parser = StrOutputParser()

# --- Step 4: 使用 LCEL 构建 Chain ---
# 摘要 Chain: article -> summary
summary_chain = summary_prompt | llm | output_parser

# 翻译 Chain: summary -> chinese_translation
# 注意: 使用字典映射将上一步的输出转换为下一步的输入键名
translate_chain = translate_prompt | llm | output_parser

# 组合成完整 Chain
# {"summary": summary_chain} 将 summary_chain 的输出包装为 {"summary": "..."} 的字典
full_chain = (
    summary_chain  # 输出: str (英文摘要)
    | (lambda summary: {"summary": summary})  # 转换键名
    | translate_chain  # 输出: str (中文翻译)
)

# --- Step 5: 执行 Chain ---
article = """
Artificial intelligence has made remarkable strides in recent years, 
particularly in the domain of large language models. These models, 
trained on vast corpora of text data, have demonstrated unprecedented 
capabilities in understanding and generating human language...
"""

# 调用方式: 输入字典中必须包含 Chain 所需的变量
result = full_chain.invoke({"article": article})
print(result)
# 输出: 中文摘要内容

# ============================================================
# 更复杂的示例: RAG Chain (Retrieval-Augmented Generation)
# 流程: 问题 -> 检索相关文档 -> 结合文档回答问题
# ============================================================

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.runnables import RunnablePassthrough

# 假设已经有一个向量数据库
embeddings = OpenAIEmbeddings()
vectorstore = FAISS.load_local("my_vectorstore", embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})  # 检索 top-3 相关文档

# 定义 RAG Prompt
rag_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful assistant. Answer the question based on the 
     provided context only. If you cannot find the answer in the context, 
     say 'I don't know'."""),
    ("human", "Context:\n{context}\n\nQuestion: {question}")
])

def format_docs(docs):
    """将检索到的文档列表格式化为字符串"""
    return "\n\n".join(doc.page_content for doc in docs)

# RAG Chain 构建
# RunnablePassthrough() 用于将原始输入透传到下一步
rag_chain = (
    {
        # 并行执行: 一路检索文档，一路透传问题
        "context": retriever | format_docs,  # 检索并格式化文档
        "question": RunnablePassthrough()     # 直接透传原始问题
    }
    | rag_prompt   # 将 context 和 question 填入模板
    | llm          # LLM 生成回答
    | output_parser  # 解析输出为字符串
)

answer = rag_chain.invoke("什么是注意力机制?")
print(answer)
```

#### Agent 示例 (带记忆)

```python
from langchain.memory import ConversationBufferMemory
from langchain.agents import create_openai_tools_agent

# ============================================================
# 带记忆的 Agent: 能够记住对话历史，实现多轮对话
# ============================================================

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# 带 chat_history 占位符的 Prompt (支持多轮对话)
agent_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant with access to various tools."),
    MessagesPlaceholder(variable_name="chat_history"),  # 历史对话占位符
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),  # Agent 推理过程占位符
])

# 使用 OpenAI Tools Agent (比 ReAct 更稳定，利用 Function Calling)
agent_with_memory = create_openai_tools_agent(
    llm=llm,
    tools=tools,
    prompt=agent_prompt
)

# 配置记忆模块
memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True  # 返回消息对象而非字符串
)

agent_executor_with_memory = AgentExecutor(
    agent=agent_with_memory,
    tools=tools,
    memory=memory,
    verbose=True,
    max_iterations=10
)

# 多轮对话示例
agent_executor_with_memory.invoke({"input": "苹果公司的股票代码是什么？"})
agent_executor_with_memory.invoke({"input": "帮我查一下它的股价"})
# 第二轮对话中，Agent 能够从 memory 中知道 "它" 指的是苹果公司 (AAPL)
```

## 2.3 简要介绍一下 engine、sub engine、skill、mcp 这几个概念，他们的用途是什么？在代码开发过程中分别用来解决什么问题？

这四个概念可以理解为一套分层协作体系：

- engine：主执行层，负责端到端任务推进。
- sub engine：子执行层，负责拆分后的专项子任务。
- skill：方法模板层，沉淀可复用的领域流程与规范。
- mcp：工具连接层，把外部系统能力标准化暴露给模型。

一句话总结：engine 管流程，sub engine 管并行与专项，skill 管方法复用，mcp 管外部能力接入。

### 一、四个概念的定义与定位

#### 1. engine (主引擎)

engine 是主控智能体或主执行引擎，负责理解用户目标、制定执行路径、调用工具、处理异常并输出最终结果。

它主要解决的问题是：复杂任务的端到端编排问题。比如“定位 bug -> 修改代码 -> 运行测试 -> 汇总结果”这种多阶段任务，不再依赖人工手动串联。

#### 2. sub engine (子引擎)

sub engine 是由主引擎派生出来的专项执行单元，通常用于独立子任务，例如：

- 代码库检索
- 文档调研
- 某个模块的局部修复
- 多方案对比

它主要解决的问题是：把大任务拆成可并行、可隔离、可回收的小任务，提高吞吐和稳定性。

#### 3. skill (技能)

skill 是可复用的“任务配方”，通常包含：

- 触发条件 (适用于什么问题)
- 步骤规范 (先做什么，后做什么)
- 质量标准 (输出要达到什么要求)

它主要解决的问题是：减少“每次都从零开始思考”的成本，保证输出风格一致、质量稳定、团队协作可复制。

#### 4. mcp (Model Context Protocol)

mcp 是模型与外部工具/数据源之间的标准协议层。通过 mcp，模型可以一致地访问数据库、代码仓库、工单系统、CI/CD、监控系统等。

它主要解决的问题是：工具接入碎片化和耦合过高问题。统一协议后，模型不必为每个系统写一套私有适配逻辑。

### 二、在代码开发中的分工

| 概念       | 在开发中的典型作用                          | 主要解决问题             |
| ---------- | ------------------------------------------- | ------------------------ |
| engine     | 总控需求分析、计划、执行、验收              | 多步骤任务如何端到端落地 |
| sub engine | 执行专项子任务 (如日志排查、依赖分析)       | 复杂任务如何拆分并行     |
| skill      | 复用成熟流程 (如“新增面试知识点”“代码审查”) | 质量一致性与效率问题     |
| mcp        | 连接外部系统能力 (Git、Issue、DB、CI)       | 工具接入标准化与可扩展性 |

### 三、一个具体开发例子

需求：修复线上接口超时问题并补回归测试。

```plaintext
engine (主控)
    ├─ 调用 sub engine A: 检索最近提交与性能日志
    ├─ 调用 sub engine B: 分析数据库慢查询与索引
    ├─ 调用 skill: "性能问题排查清单" (固定排查顺序)
    ├─ 通过 mcp 访问: Git、监控平台、工单系统、CI
    └─ 汇总修复方案 -> 提交代码 -> 触发测试 -> 生成结论
```

在这个过程中：

- 没有 engine，会缺少全局编排，容易只修局部不闭环。
- 没有 sub engine，所有分析串行进行，速度慢且上下文易混乱。
- 没有 skill，每次排查路径都不同，质量不稳定。
- 没有 mcp，工具调用需要大量定制代码，维护成本高。

### 四、边界与常见误区

#### 1. 误区：sub engine 等于更多模型调用，越多越好

错误。子引擎过多会增加协调成本和冲突概率。应按任务天然边界拆分，而不是机械并行。

#### 2. 误区：skill 只是提示词模板

不完整。高质量 skill 不仅有提示词，还应包含步骤约束、输出格式、验收标准。

#### 3. 误区：mcp 只是“工具插件市场”

错误。mcp 的核心价值是协议标准化与上下文对齐，不只是“能调用工具”，而是“稳定、可审计、可扩展地调用工具”。

### 五、面试回答模板 (可直接复述)

可以这样回答：engine 是主控执行层，负责把用户目标转成可落地流程并闭环交付；sub engine 是子任务执行层，解决复杂任务拆分与并行效率；skill 是可复用的方法模板，保证不同任务下的质量一致性；mcp 是模型与外部系统的标准连接层，解决工具接入碎片化问题。在实际开发里，这四者分别对应“总控、分工、方法、连接”，组合起来能显著提升 AI 辅助开发的效率和稳定性。

### 知识扩展

- Workflow Orchestration：engine/sub engine 本质是工作流编排问题，可与 DAG、状态机思想结合。
- Prompt Engineering 与 Policy：skill 往往要和规则约束一起设计，避免输出漂移。
- Tool Use Reliability：mcp 的稳定性直接影响 agent 实际可用性，需关注超时、重试、权限与审计。
- Human-in-the-loop：高风险改动应保留人工审批节点，形成“自动执行 + 人工兜底”的混合流程。

## 2.4 Workflow、Agent、Tools 这三个概念分别是什么？核心区别是什么？

这个问题在面试里非常高频，建议用一句话先定边界：

- Workflow 是流程编排层，定义任务怎么被拆解和执行。
- Agent 是决策执行层，负责在运行时思考下一步做什么。
- Tools 是能力原子层，负责执行具体动作 (查、算、读、写、调接口)。

一句话总结：Workflow 决定流程骨架，Agent 决定动态路径，Tools 提供可调用能力。

### 一、三个概念的定义与职责

#### 1. Workflow (工作流)

Workflow 是对任务步骤、依赖关系、状态流转、异常处理的显式编排。它通常是确定性的，强调“可控性、可观测性、可恢复性”。

典型能力包括：

- DAG 或状态机建模 (哪些步骤串行，哪些并行)
- 重试与超时策略
- 人工审批节点 (Human-in-the-loop)
- 失败补偿与断点续跑

本质上，Workflow 回答的是：任务应该按什么流程推进。

#### 2. Agent (智能体)

Agent 是以 LLM 为核心决策器的执行单元，会根据当前上下文和反馈动态选择下一步动作。它不是固定脚本，而是“边观察边决策”。

典型能力包括：

- 任务分解与规划 (Plan)
- 工具选择与参数生成 (Act)
- 读取工具反馈并修正策略 (Observe -> Replan)
- 在目标满足时停止 (Terminate)

本质上，Agent 回答的是：当前时刻最应该做什么。

#### 3. Tools (工具)

Tools 是可被模型调用的外部能力接口，通常具备明确输入输出 schema。

常见工具类型：

- 检索类：搜索、RAG Retriever、数据库查询
- 执行类：代码执行、SQL 执行、Shell 命令
- 业务类：订单系统、工单系统、风控系统 API
- 系统类：文件读写、邮件发送、日历管理

本质上，Tools 回答的是：具体动作由谁来执行，以及以什么协议执行。

### 二、核心区别 (从控制权视角看)

| 维度     | Workflow         | Agent             | Tools                   |
| -------- | ---------------- | ----------------- | ----------------------- |
| 关注点   | 流程结构与治理   | 动态决策与推理    | 具体能力执行            |
| 控制权   | 开发者预定义为主 | 运行时由模型决定  | 由外部系统实现          |
| 稳定性   | 高               | 中 (依赖模型行为) | 高 (工程可控)           |
| 灵活性   | 中               | 高                | 低到中 (取决于接口设计) |
| 可观测性 | 强 (节点级)      | 中 (需记录轨迹)   | 强 (调用日志)           |
| 失败处理 | 重试/补偿/回滚   | 反思/改计划/降级  | 超时/重试/熔断          |

可以用一个分层结构记忆：

```plaintext
用户目标
    ↓
Workflow (编排层)
    ↓ 调度
Agent (决策层)
    ↓ 调用
Tools (能力层)
    ↓ 返回 Observation
Agent 更新策略 -> Workflow 判断是否收敛
```

### 三、为什么三者不能互相替代

#### 1. 只有 Agent + Tools，没有 Workflow

问题：复杂任务缺少全局治理，容易出现长链路失控 (无限循环、失败不可恢复、审计困难)。

#### 2. 只有 Workflow + Tools，没有 Agent

问题：面对开放问题时策略刚性高，缺乏运行时自适应，遇到异常输入时泛化差。

#### 3. 只有 Workflow + Agent，没有 Tools

问题：模型只能“说”，不能“做”，最终难以与真实系统交互落地。

### 四、工程落地示例 (可直接在面试中复述)

场景：自动化事故分析与修复建议。

```plaintext
Workflow:
  Step1 拉取告警 -> Step2 定位服务 -> Step3 调Agent分析 -> Step4 生成修复建议 -> Step5 人工确认 -> Step6 执行变更

Agent:
  根据日志和指标动态决定先查 APM、再查最近发布、再查数据库慢查询

Tools:
  get_metrics(), query_logs(), get_recent_deploy(), run_sql_explain(), create_incident_report()
```

在这条链路里：

- Workflow 保证流程可审计、可回滚。
- Agent 保证问题排查路径具备自适应能力。
- Tools 保证每一步能真正访问外部系统并获得可验证结果。

### 五、常见误区与边界

#### 1. 误区：Agent 越强就不需要 Workflow

错误。Agent 解决的是局部决策，不解决系统级治理 (SLA、审批、审计、补偿)。

#### 2. 误区：Tools 就是简单函数封装

不完整。生产级 Tool 还需要权限控制、参数校验、幂等保障、超时重试、审计日志。

#### 3. 误区：Workflow 一定是固定死流程

不准确。现代 Workflow 通常是“确定性骨架 + Agent 弹性节点”，兼顾稳定与灵活。

### 六、面试回答模板 (30 秒版本)

可以这样回答：Workflow、Agent、Tools 是 AI 系统里的三层抽象。Workflow 负责全局流程编排和治理，确保任务可控、可审计、可恢复；Agent 负责运行时动态决策，通过推理选择下一步动作；Tools 负责执行具体动作并返回可验证结果。三者的关系是 Workflow 调度 Agent，Agent 调用 Tools，Tools 的反馈再反哺 Agent 决策。工程上通常采用“确定性 Workflow + 局部 Agent + 可靠 Tools”的组合，这样既有稳定性，也有复杂场景下的适应能力。

### 知识扩展

- ReAct：Agent 的核心闭环就是 Thought -> Action -> Observation，Tools 对应 Action 的执行端。
- Function Calling 与 MCP：两者都是 Tool 接入的关键基础设施，前者偏模型侧结构化调用，后者偏跨系统协议标准化。
- Multi-Agent：当单 Agent 上下文和责任过大时，可拆为规划 Agent、执行 Agent、评审 Agent，通过 Workflow 协调。
- Reliability Engineering：Workflow 中的重试、熔断、补偿、幂等设计决定了 Agent 系统能否稳定上线。

## 2.5 有哪些 Agent 设计范式？它们分别适合什么场景？

如果把 Agent 理解成“让模型自己决定下一步怎么做”的系统，那么设计范式就是“这个决定过程如何组织”。不同范式的核心差异不在于是否会调用工具，而在于：是先想后做，边想边做，还是多角色协作、由工作流托底。

一句话总结：Agent 设计范式的本质，是在“灵活性、可控性、稳定性、成本”之间做不同权衡。

### 一、常见 Agent 设计范式总览

| 范式                    | 核心思想                                      | 优点                 | 缺点                     | 适用场景                           |
| ----------------------- | --------------------------------------------- | -------------------- | ------------------------ | ---------------------------------- |
| ReAct                   | 边推理边行动，Observation 驱动下一步          | 灵活、直观、实现简单 | 容易发散、步数不可控     | 开放问答、工具使用、探索性任务     |
| Plan-and-Execute        | 先规划，再逐步执行                            | 结构清晰、可控性强   | 规划错误会层层放大       | 长任务、流程明确的复杂任务         |
| Tool-Calling Agent      | 通过 Function Calling / Tool Calling 触发工具 | 调用稳定、工程友好   | 对复杂推理的表达力有限   | 搜索、查询、业务接口调用           |
| Reflection / Critic     | 执行后自我反思并修正                          | 结果质量更高         | 额外推理成本高           | 代码生成、文本改写、方案评审       |
| Router / Dispatcher     | 先判断任务类型，再路由到专用子链路            | 专业化强、可维护     | 路由器本身需要训练/设计  | 多意图助手、多业务域系统           |
| Multi-Agent             | 多个 Agent 分工协作                           | 适合复杂协同任务     | 协调成本高、容易互相干扰 | 研究助手、软件工程协作、团队式任务 |
| Workflow + Agent Hybrid | 用工作流做骨架，Agent 做弹性决策              | 稳定与灵活兼顾       | 设计复杂、需要边界清晰   | 生产级智能体系统                   |

### 二、逐个解释这些范式

#### 1. ReAct 范式

ReAct (Reasoning + Acting) 是最经典的 Agent 范式，它把“思考”和“行动”交替起来：先根据当前上下文做一步推理，再选择一个工具行动，读取结果后继续推理。

典型流程：

```plaintext
问题 -> Thought -> Action -> Observation -> Thought -> Action -> ... -> Final Answer
```

它的优点是通用、自然，特别适合需要不断试探和修正的任务；缺点是步数不固定，容易在复杂问题上反复试错。

#### 2. Plan-and-Execute 范式

这种范式先由 LLM 生成一个整体计划，再把计划拆成多个子步骤逐个执行。它强调“先定路线，再开车”。

适合场景：

- 论文调研
- 长链路数据分析
- 多步代码修改
- 需要明确里程碑的任务

它的关键问题是规划质量：如果初始计划错了，后面的执行再好也可能偏离目标，所以通常要配合中途检查和重新规划。

#### 3. Tool-Calling Agent 范式

这种范式把 Agent 的动作空间收敛到“调用工具”上，模型不再自由输出大段中间推理，而是输出结构化的工具调用请求。

核心特点：

- 依赖 Function Calling 或 Tool Calling schema
- 工具输入输出明确
- 工程上更稳定、可审计

这类范式非常适合生产环境，因为它能把模型行为限制在可验证的范围内，降低胡乱发挥的概率。

#### 4. Reflection / Critic 范式

这种范式允许 Agent 对自己的结果进行自我批判或由另一个 Critic 模块进行审查，然后再修正输出。它常见于“先生成，再评估，再修改”的流程。

适合场景：

- 代码修复
- 文案润色
- 方案评审
- 数学推理验证

它的价值在于提高结果质量，但代价是推理轮次更多、延迟更高。

#### 5. Router / Dispatcher 范式

Router 范式不是让一个 Agent 什么都做，而是先判断任务属于哪一类，再路由到专门的处理链路。例如：

- 搜索问题 -> 检索链路
- 计算问题 -> 计算工具
- 数据分析 -> SQL + 图表链路
- 代码问题 -> 代码 Agent

这种方式的核心是“专人专岗”，可以显著提升稳定性和可维护性。

#### 6. Multi-Agent 范式

Multi-Agent 是把单个 Agent 的职责拆成多个角色协同工作，例如：

- Planner：负责规划
- Executor：负责执行
- Reviewer：负责审核
- Retriever：负责检索

它适合任务复杂、需要多视角协作的场景，比如软件工程、研究分析、复杂运营自动化。但它的协调成本高，容易出现信息不一致、重复劳动、状态同步困难等问题。

#### 7. Workflow + Agent Hybrid 范式

这是工业界最常见、也最实用的范式之一。它不是单纯让 Agent 自由发挥，而是把整条链路放进一个 Workflow 中，由 Workflow 负责节点顺序、状态流转、失败重试和人工审批，Agent 只负责其中最需要智能判断的部分。

这类模式通常是：

- Workflow 管大框架
- Agent 管局部不确定性
- Tools 管具体执行

### 三、如何选择合适的设计范式

可以按任务特征来判断：

1. 如果任务步骤固定，优先用 Workflow 或 Tool-Calling Agent。
2. 如果任务需要边做边判断，优先用 ReAct。
3. 如果任务很长、目标明确，优先用 Plan-and-Execute。
4. 如果结果质量要求高，加入 Reflection / Critic。
5. 如果任务类型很多，优先用 Router。
6. 如果任务天然需要多角色协作，考虑 Multi-Agent。
7. 如果是生产级系统，优先考虑 Workflow + Agent Hybrid。

### 四、工程实践中的典型架构

一个比较稳妥的生产架构通常不是“纯 Agent”，而是下面这种组合：

```plaintext
用户请求
    ↓
Router 判别意图
    ↓
Workflow 编排主流程
    ↓
Agent 处理不确定步骤
    ↓
Tools 执行外部动作
    ↓
Critic 做结果校验
    ↓
返回结果 / 触发重试 / 人工确认
```

这个架构的好处是：

- 重要节点可审计
- 复杂步骤可拆分
- 模型能力只用在最需要它的地方
- 整体更容易上线和维护

### 五、容易混淆的点

#### 1. ReAct 和 Plan-and-Execute 的区别

ReAct 是边想边做，适合探索式任务；Plan-and-Execute 是先整体规划再逐步执行，适合长任务和高可控场景。

#### 2. Multi-Agent 不一定比单 Agent 更强

多 Agent 并不是“越多越好”，如果角色边界不清晰，只会增加通信开销和出错概率。

#### 3. Tool-Calling 不等于 Agent 完整能力

Tool-Calling 解决的是“怎么安全地调工具”，不自动解决“怎么规划、怎么反思、怎么收敛”。

#### 4. Workflow 不是 Agent 的对立面

工业落地里，Workflow 往往是 Agent 的外层约束，而不是替代品。

### 六、面试回答模板 (可直接复述)

可以这样回答：Agent 的设计范式主要有 ReAct、Plan-and-Execute、Tool-Calling、Reflection、Router、Multi-Agent，以及 Workflow + Agent Hybrid。ReAct 适合边推理边执行的开放任务；Plan-and-Execute 适合长任务和明确目标；Tool-Calling 更偏生产级工具调用；Reflection 用来提升结果质量；Router 负责意图分发；Multi-Agent 适合多角色协作；而工业界最常见的是 Workflow + Agent Hybrid，因为它能在可控性和灵活性之间取得平衡。

### 知识扩展

- ReAct：是最基础的“思考 + 行动”闭环，很多 Agent 设计都建立在它之上。
- Function Calling：是 Tool-Calling Agent 的核心工程基础。
- Plan-and-Execute：和任务分解、子目标管理、长链路执行强相关。
- Multi-Agent：和角色分工、消息传递协议、共享记忆强相关。
- Workflow Orchestration：是生产级 Agent 系统的外层治理框架。

## 2.6 Agent 推理模式有哪些？具体是怎么实现的？

Agent 的推理模式，本质上是“模型在做决策时，内部思考、规划、行动、反思这几个环节如何组织”。不同模式的区别，不只是输出格式不同，而是控制循环的方式不同：有的模式是一次性推理，有的是边想边做，有的是先规划再执行，还有的是执行后自我修正。

一句话总结：Agent 推理模式就是把“如何想”和“如何做”拆成不同的运行时策略。

### 一、常见推理模式总览

| 推理模式                       | 核心思想             | 优点                 | 缺点               | 适用场景             |
| ------------------------------ | -------------------- | -------------------- | ------------------ | -------------------- |
| Direct Answer                  | 一次性直接生成答案   | 快、简单、成本低     | 不适合复杂任务     | 简单问答、已知事实   |
| CoT (Chain of Thought)         | 显式生成中间推理步骤 | 推理能力更强         | 成本高，容易冗长   | 数学、逻辑、复杂分析 |
| ReAct                          | 推理和行动交替进行   | 能用工具纠错         | 过程长、易发散     | 搜索、查询、开放任务 |
| Plan-and-Execute               | 先规划，再逐步执行   | 结构清晰、可控性强   | 初始计划错误会放大 | 长任务、多步骤任务   |
| Reflexion / Critic             | 执行后反思，再修正   | 结果更稳、更准       | 轮次更多、延迟更高 | 代码修复、方案优化   |
| Tree / Graph of Thoughts       | 同时探索多个推理分支 | 覆盖更全面           | 计算成本高         | 复杂推理、搜索问题   |
| Debate / Multi-Agent Reasoning | 多个 Agent 相互讨论  | 观点互补、鲁棒性更强 | 协调成本高         | 评审、决策、研究场景 |

### 二、逐个解释这些推理模式

#### 1. Direct Answer 模式

这是最基础的方式，模型直接根据输入生成最终答案，不显式展开中间推理。

它的实现最简单：

```plaintext
User Input -> LLM -> Final Answer
```

这种方式适合事实性强、步骤简单、无需工具的任务，但不适合复杂决策场景，因为缺少中间检查点。

#### 2. CoT (Chain of Thought) 模式

CoT 的核心是让模型先生成中间推理过程，再给出最终答案。它的作用是把隐式推理变成显式推理，从而提升复杂任务的正确率。

实现方式通常有两种：

- Prompt CoT：在提示词里显式要求“逐步思考”
- Hidden Scratchpad：把推理过程放在内部草稿区，不直接展示给用户

示意：

```plaintext
Prompt -> Thought 1 -> Thought 2 -> ... -> Final Answer
```

在工程中，CoT 常用于规划前分析、复杂问答和判断类任务，但如果直接暴露完整思维链，可能带来冗长输出和安全/可控性问题，所以生产系统常会把中间推理隐藏起来，只保留可审计摘要。

#### 3. ReAct 模式

ReAct (Reasoning + Acting) 是 Agent 最经典的推理模式，它把“想”和“做”交替起来。模型先思考当前最需要做什么，再调用工具行动，读取结果后继续推理。

它的运行循环通常是：

```plaintext
Observation -> Thought -> Action -> Observation -> ... -> Final Answer
```

实现上，一般包含三个组件：

- Prompt 模板：包含 system 指令、用户输入、scratchpad
- Tool Executor：负责真正调用外部工具
- Loop Controller：负责把 Observation 回填给模型并决定是否继续

一个简化伪代码如下：

```python
state = {"messages": [user_input]}

while True:
     # 1. 模型根据当前状态生成下一步推理或动作
     output = llm.invoke(state)

     if output.is_final:
          return output.final_answer

     # 2. 解析工具调用
     tool_name, tool_args = parse_action(output)

     # 3. 执行工具并拿到观察结果
     observation = tools[tool_name](**tool_args)

     # 4. 把观察结果写回上下文，进入下一轮推理
     state["messages"].append({"role": "assistant", "content": output.thought})
     state["messages"].append({"role": "tool", "content": observation})
```

ReAct 的关键不是“会不会调用工具”，而是“能不能根据工具反馈持续修正决策”。

#### 4. Plan-and-Execute 模式

这种模式把推理拆成两个阶段：先由 Planner 生成完整计划，再由 Executor 按步骤执行。

实现流程通常是：

```plaintext
User Input -> Planner -> Plan List -> Executor -> Step Results -> Final Answer
```

典型实现会把计划结构化成 JSON，例如：

```json
{
  "goal": "分析接口超时原因",
  "steps": [
     {"id": 1, "task": "拉取最近告警"},
     {"id": 2, "task": "查看最近发布记录"},
     {"id": 3, "task": "分析慢查询和调用链"}
  ]
}
```

Executor 负责逐步执行，如果某一步失败，可以触发局部重试或重新规划。这个模式非常适合长任务，因为它把“推理”和“执行”解耦了。

#### 5. Reflexion / Critic 模式

这种模式在第一次执行后，会增加一个反思环节，对结果进行自我检查或由 Critic Agent 审核，再决定是否修正。

常见流程：

```plaintext
Draft -> Critique -> Revision -> Final Answer
```

实现方式可以是：

- 同一个模型两次调用：第一次生成，第二次评审
- 双模型架构：一个 Generator + 一个 Critic
- 评分函数驱动：根据规则或指标决定是否重写

这个模式的价值在于提升最终质量，尤其适合代码修复、方案评审和高准确率内容生成。

#### 6. Tree / Graph of Thoughts 模式

这类模式不是只沿着一条思路推到底，而是同时探索多个候选推理分支，再对分支进行评分、剪枝和合并。

可以理解为：

```plaintext
State 0 -> Branch A -> Score
          -> Branch B -> Score
          -> Branch C -> Score
```

实现上通常要有三步：

- 生成多个候选中间状态
- 对候选状态打分或排序
- 保留更优分支继续扩展

这个模式更像搜索算法与 LLM 的结合，适合高难度推理题，但成本也最高。

#### 7. Debate / Multi-Agent Reasoning 模式

这种模式让多个 Agent 从不同角度提出观点、互相质疑、互相修正，最后由裁判或汇总器给出结论。

典型角色可以是：

- Proposer：提出方案
- Challenger：质疑方案
- Judge：整合并裁决

实现上，本质是“多轮消息传递 + 共享状态 + 裁决机制”。它适合需要更高鲁棒性的任务，但协调成本较高。

### 三、这些模式在工程上怎么实现

无论是哪种推理模式，工程实现通常都离不开下面几个组件：

1. Prompt 设计
    用 system prompt 约束模型的推理风格、输出结构和工具使用方式。
2. State 管理
    把当前思考、工具返回、计划列表、历史结果保存起来。
3. Loop Controller
    决定什么时候继续推理，什么时候结束。
4. Tool Executor
    真正执行外部动作，并把结果回填给模型。
5. Critic / Scorer
    对中间结果进行评估、打分、纠错或重排。

如果从实现框架看，很多 Agent 系统本质上是一个状态机或有向图：

```plaintext
Start -> Plan -> Act -> Observe -> Reflect -> Finish
             ↑                      ↓
             └──────── Replan ←──────┘
```

这也是为什么 LangGraph 很适合做复杂 Agent，因为它天然支持“节点 + 边 + 条件跳转”的推理循环。

### 四、如何选择推理模式

可以按任务复杂度来判断：

1. 简单事实问答：Direct Answer 或轻量 Tool-Calling。
2. 需要多步逻辑：CoT 或 ReAct。
3. 长任务和明确目标：Plan-and-Execute。
4. 结果质量要求高：Reflection / Critic。
5. 搜索空间大、答案不唯一：Tree / Graph of Thoughts。
6. 需要多视角协作：Debate / Multi-Agent Reasoning。

生产系统里，最常见的不是单一模式，而是组合模式，比如：

- Router 先分类
- ReAct 处理中间不确定步骤
- Critic 做结果校验
- Workflow 负责失败重试和审批

### 五、容易混淆的点

#### 1. CoT 和 ReAct 不是一回事

CoT 主要是“显式推理”，ReAct 是“推理 + 工具行动”的循环。

#### 2. Plan-and-Execute 不等于一定更好

如果任务本身很短，强行规划反而增加延迟和失败点。

#### 3. 推理模式不等于训练方法

推理模式是运行时策略，SFT、RLHF、DPO 是训练方法，两者有关联但不是一回事。

#### 4. 反思模式不一定提升所有任务

它会增加成本，简单任务上可能得不偿失。

### 六、面试回答模板 (可直接复述)

可以这样回答：Agent 的推理模式常见有 Direct Answer、CoT、ReAct、Plan-and-Execute、Reflection / Critic、Tree / Graph of Thoughts 和 Debate / Multi-Agent Reasoning。Direct Answer 适合简单任务，CoT 适合复杂逻辑推理，ReAct 适合边想边用工具，Plan-and-Execute 适合长任务，Reflection 用来提升结果质量，Tree / Graph of Thoughts 用来搜索多个推理分支，多 Agent Debate 适合多角色协作。工程上通常把这些模式实现为一个状态机或图结构，通过 prompt、state、tool executor、loop controller 和 critic 共同完成推理闭环。

### 知识扩展

- ReAct：最经典的推理 + 行动闭环，很多 Agent 框架都建立在它之上。
- LangGraph：非常适合把推理模式实现成状态机或图结构工作流。
- Function Calling：是 ReAct 和 Tool-Calling 模式的关键执行基础。
- SFT / RLHF / DPO：这些训练方法会影响模型更擅长哪类推理模式。
- Self-Consistency：和 CoT、Tree of Thoughts 强相关，常用于提升答案稳定性。

## 2.7 在开发 Agent 时，如果遇到上下文爆炸或工具循环调用等问题，你会怎么解决？

这是一个非常工程化的问题，面试里建议先给结论：

- 上下文爆炸本质是“信息增长速度 > 上下文预算”。
- 工具循环调用本质是“状态收敛条件不清晰 + 决策反馈不稳定”。

一句话总结：要把 Agent 从“会跑”升级到“可控可收敛”，核心是预算管理、状态压缩、调用治理和终止条件设计。

### 一、先把问题拆清楚

#### 1. 上下文爆炸的典型表现

- 会话越长，延迟和成本线性上升甚至失控。
- 模型出现 Lost in the Middle，中段关键信息利用率下降。
- 工具返回原始大文本，导致后续轮次提示词被噪声淹没。
- 多 Agent 协作时，彼此转发完整历史，造成 token 级联膨胀。

#### 2. 工具循环调用的典型表现

- 同一工具被重复调用，参数仅有微小变化。
- 工具错误后反复重试但没有策略更新。
- Agent 在“搜索 -> 再搜索 -> 再搜索”中无法停机。
- 最终答案迟迟不输出，或者输出前已消耗大量无效调用。

### 二、解决上下文爆炸的核心手段

#### 1. 分层记忆，而不是全量拼接

把上下文分为三层：

- 短期工作记忆：保留最近 N 轮原始消息。
- 中期摘要记忆：把较早对话压缩成结构化摘要。
- 长期检索记忆：只在需要时通过向量检索召回。

核心思想是“保留必要原文 + 压缩历史 + 按需召回”，而不是把所有历史都塞进提示词。

#### 2. 做上下文预算 (Context Budgeting)

每轮推理前先分配 token 预算，例如：

$$
B_{total} = B_{system} + B_{history} + B_{tools} + B_{output}
$$

并设置硬阈值：

- `history` 超阈值就触发摘要压缩
- `tools` 超阈值就做结果裁剪或结构化抽取
- 为 `output` 预留固定预算，防止答案被截断

#### 3. 工具结果先结构化再入上下文

不要直接把工具原始响应 (HTML、长日志、全量 JSON) 回填给模型，而是先做标准化抽取：

- 保留关键字段
- 去掉冗余噪声
- 附带来源和置信度

例如，把日志工具输出压成：

```json
{
  "error_type": "DBTimeout",
  "top_trace": "OrderService -> DAO -> MySQL",
  "p95_ms": 1840,
  "time_range": "10:00-10:15"
}
```

这样可以显著降低 token 消耗，并提升下一轮推理的可控性。

#### 4. 使用滑动窗口 + 关键帧机制

滑动窗口只保留近期原文，同时维护关键帧 (Milestones)：

- 用户目标
- 已验证事实
- 已完成步骤
- 待办步骤

这样即便历史被裁剪，Agent 也不会丢失主线任务状态。

### 三、解决工具循环调用的核心手段

#### 1. 明确停止条件 (Stop Conditions)

每个 Agent 循环必须具备强约束，例如：

- 最大工具调用次数 `max_tool_calls`
- 最大推理轮次 `max_iterations`
- 连续无增益调用上限 `max_no_progress`
- 达成目标即提前终止 `goal_satisfied`

没有终止条件的 Agent，线上必然出现循环风险。

#### 2. 引入“进展函数”判断是否在收敛

定义一个 progress score 来判断每轮是否有有效推进，例如：

$$
P_t = w_1 \cdot \Delta facts + w_2 \cdot \Delta confidence + w_3 \cdot \Delta plan\_completion
$$

如果连续 $k$ 轮 $P_t \le 0$，触发降级策略 (停止、换工具、请求用户澄清)。

#### 3. 对工具调用做去重与幂等保护

为调用签名建立缓存键：

- `signature = hash(tool_name + normalized_args)`
- 相同签名短时间内禁止重复调用
- 对可缓存工具优先命中缓存

这可以直接消除“同参数反复调同工具”的死循环。

#### 4. 错误分级 + 有限重试

工具异常要区分：

- 可重试错误 (超时、429、临时网络波动)
- 不可重试错误 (参数非法、权限不足、资源不存在)

策略示例：

- 可重试错误：指数退避重试 1 ~ 2 次
- 不可重试错误：立即反馈模型并要求更改策略

这样可以避免“错误 -> 重试 -> 再错 -> 再重试”的空转。

### 四、一个可落地的控制器伪代码

```python
max_iterations = 12
max_tool_calls = 8
max_no_progress = 2

tool_calls = 0
no_progress_rounds = 0
seen_signatures = set()
state = init_state(user_goal)

for i in range(max_iterations):
    state = apply_context_budget(state)  # 摘要压缩 + 检索召回 + 工具结果裁剪
    action = planner_or_agent(state)

    if action.type == "final_answer":
        return action.answer

    sig = signature(action.tool, action.args)
    if sig in seen_signatures:
        no_progress_rounds += 1
        if no_progress_rounds > max_no_progress:
            return fallback_answer("检测到重复调用，已停止并返回当前最优结论")
        continue

    seen_signatures.add(sig)
    result = execute_tool_with_retry(action.tool, action.args)
    tool_calls += 1

    if tool_calls >= max_tool_calls:
        return fallback_answer("达到工具调用上限，建议用户补充信息")

    progress = evaluate_progress(state, result)
    no_progress_rounds = 0 if progress > 0 else no_progress_rounds + 1

    state = update_state(state, action, result)

return fallback_answer("达到最大迭代轮次，返回当前可验证结论")
```

这个控制器的关键点是四件事：预算、去重、进展检测、强制停机。

### 五、工程实践建议 (生产可用)

1. 观测性先行
   为每次调用记录 `trace_id`、token 消耗、工具调用链、终止原因。
2. 灰度和熔断
   新 Agent 策略先小流量灰度，异常率超阈值自动熔断。
3. 人工兜底
   当达到循环阈值或低置信度时，切换到人工确认模式。
4. 策略分层
   Router 先分流简单问题，复杂问题才进入高成本 Agent 循环。

### 六、容易踩坑的误区

#### 1. 只加大上下文窗口就能解决上下文爆炸

不准确。窗口变大只能延后问题，不会消除噪声累积和注意力稀释。

#### 2. 循环调用只靠 max iterations 就够了

不够。没有“进展判定 + 去重机制”，会在限制内持续空转。

#### 3. 工具返回越完整越好

错误。Agent 需要的是“可决策信息”，不是“全量原始数据”。

#### 4. 所有错误都自动重试

危险。参数错误和权限错误应尽快暴露并改策略，而不是盲目重试。

### 七、面试回答模板 (可直接复述)

可以这样回答：我会把这个问题分为“上下文治理”和“调用治理”两部分。上下文爆炸方面，我会做分层记忆、上下文预算、工具结果结构化和滑动窗口关键帧，确保 token 可控且主线信息不丢。工具循环方面，我会设置最大轮次/最大调用次数、调用签名去重、进展函数监控和错误分级重试，并配置强制停机与降级兜底。生产上再配合 tracing、灰度和人工接管，才能把 Agent 做到可控、可收敛、可运维。

### 知识扩展

- Memory Architecture：分层记忆和摘要策略是解决上下文膨胀的基础。
- Tool Calling Reliability：幂等、重试、超时、熔断直接决定循环风险。
- LangGraph / State Machine：非常适合实现“条件跳转 + 强制终止”控制逻辑。
- Evals 与在线监控：需要持续评估“成功率、循环率、平均调用步数、单位任务成本”。
- Human-in-the-loop：在高风险或低置信度场景中是必要安全阀。

## 2.8 复杂 Agent 是如何实现自我纠正 (Self-Correction) 和不断进化的？在状态机 (如 LangGraph) 中，如果中间有一步出错，如何处理状态回滚和重新生成？

这是一个典型的"从 Demo 到生产"问题。面试里先给一句结论会更稳：复杂 Agent 的自我纠正不是靠一次 Prompt 技巧完成，而是靠“可观测状态机 + 误差检测 + 回滚重试 + 策略更新”的闭环系统。

### 一、先拆解 Self-Correction 的本质

Agent 自我纠正可以拆成四个阶段：

1. 检测 (Detect)：识别当前步骤是否失败或低置信。
2. 归因 (Diagnose)：判断是计划错误、工具错误、数据错误还是约束冲突。
3. 修复 (Recover)：回滚到稳定状态，选择重试、换路由或降级。
4. 学习 (Learn)：将这次失败沉淀为策略，减少下次同类错误。

可以把它写成一个闭环：

$$
Policy_{t+1} = Policy_t + \Delta(Feedback, Failure\ Pattern, Reward)
$$

这里的 `Feedback` 既可以是规则评估器，也可以是用户反馈和人工标注。
### 二、复杂 Agent 的自我纠正架构

#### 1. 双层纠错机制

- 局部纠错 (Step-level)：每个节点执行后立刻校验，避免错误扩散。
- 全局纠错 (Trajectory-level)：任务结束前做一致性检查，避免局部正确但全局跑偏。

#### 2. 常见误差检测器

- Schema Validator：检查工具输出是否满足 JSON/字段约束。
- Constraint Checker：检查是否违反预算、权限、业务规则。
- Consistency Checker：检查当前结论与历史事实是否冲突。
- Grounding Checker：检查答案是否有证据支撑，防止幻觉。

#### 3. 修复策略优先级

一般按成本从低到高：

1. 参数修正后重试同一工具。
2. 同任务换工具或换检索源。
3. 回滚到上一个稳定节点重新规划。
4. 降级为保守回答或请求用户澄清。
5. 触发人工接管。

### 三、在状态机 (LangGraph) 里如何做回滚和重生成

核心思想是把每个节点执行前后的状态做快照 (Snapshot)，并定义明确的提交点 (Commit Point)。只有通过校验的状态才提交，否则回滚。

#### 1. 推荐状态模型

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class AgentState:
    trace_id: str
    step_id: int
    plan: list[str] = field(default_factory=list)
    facts: dict[str, Any] = field(default_factory=dict)
    tool_outputs: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    retry_count: int = 0
    confidence: float = 1.0
    checkpoint_id: str | None = None
```

这个结构要点是：`plan`、`facts`、`tool_outputs` 分开存，便于精确回滚而不是整段对话回滚。

#### 2. 节点执行的事务化流程

```text
Load Last Checkpoint
-> Execute Node
-> Validate Output
-> Pass ? Commit : Rollback
-> Replan / Retry / Fallback
```

在 LangGraph 中可以把 `validate` 和 `route_on_error` 做成显式节点，利用条件边进行跳转。

#### 3. 回滚策略设计

- 软回滚 (Soft Rollback)：只清理当前失败节点产物，保留已验证事实。
- 硬回滚 (Hard Rollback)：回退到最近提交点，重新规划后继续。
- 语义回滚 (Semantic Rollback)：不回退全部状态，只撤销被污染的事实子集。

语义回滚在多工具并行场景尤其重要，否则会把无关正确结果也一并丢弃。

#### 4. 重新生成 (Regeneration) 的三种模式

1. Same Plan Retry：计划不变，仅修参数或提示词。
2. Partial Replan：只重写失败子任务，不影响已完成分支。
3. Full Replan：当依赖链被破坏时，整条路径重规划。

可用简单决策规则：

$$
mode=
\begin{cases}
retry, & error\_type\in\{timeout, transient\} \\
partial\_replan, & local\ dependency\ broken \\
full\_replan, & global\ constraints\ conflict
\end{cases}
$$

### 四、一个可落地的状态回滚伪代码

```python
def run_step_with_recovery(graph, state, node_name, store):
    # 1) 执行前快照
    ckpt = store.save_checkpoint(state)

    try:
        new_state = graph.run_node(node_name, state)

        # 2) 执行后校验
        ok, reason = validate_state(new_state)
        if ok:
            store.commit(ckpt, new_state)
            return new_state

        # 3) 校验失败 -> 回滚
        rolled = store.rollback(ckpt)
        rolled.errors.append(reason)
        rolled.retry_count += 1

        # 4) 策略分流
        if rolled.retry_count <= 2 and is_transient(reason):
            return graph.run_node(node_name, patch_for_retry(rolled, reason))
        if is_local_failure(reason):
            return graph.run_node("partial_replan", rolled)
        return graph.run_node("full_replan", rolled)

    except Exception as e:
        rolled = store.rollback(ckpt)
        rolled.errors.append(f"runtime_exception: {str(e)}")
        return graph.run_node("fallback_or_human", rolled)
```

这段流程的核心是三件事：先快照、后提交、失败即回滚。

### 五、如何实现“不断进化”而不是“每次从零纠错”

#### 1. 失败样本沉淀为经验库

把以下信息写入经验库：

- 任务类型、输入特征
- 错误类型、触发节点
- 最终修复动作及效果

后续路由器可以优先使用历史上成功率更高的策略。

#### 2. 在线评估驱动策略更新

建议持续监控：

- First Pass Success Rate
- Recovery Success Rate
- Mean Steps To Recovery
- Rollback Frequency
- Cost Per Successful Task

当某类错误频率上升时，自动触发策略回归测试与灰度发布。

#### 3. 人类反馈闭环

对高价值失败案例做人工标注，更新：

- 路由规则
- 提示词模板
- 工具参数默认值
- 校验器规则

这样进化路径是可解释、可审计的，而不是黑盒“自动变好”。

### 六、常见误区

1. 误区：只要加一个 Reflection 节点就算自我纠正。
   没有状态提交与回滚机制，Reflection 只能“发现问题”，不能“稳定修复”。
2. 误区：失败就全量重跑最安全。
   全量重跑成本高且不稳定，应优先局部回滚和局部重规划。
3. 误区：错误重试次数越多越好。
   无归因的盲重试只会放大成本，必须配合错误分类和重试门限。
4. 误区：进化只看离线指标。
   线上行为漂移很常见，必须有在线指标和灰度机制。

### 七、面试可直接复述的总结

可以这样回答：复杂 Agent 的 Self-Correction 本质是一个闭环控制系统，我会在状态机里把每个节点做成“快照-执行-校验-提交”的事务流程，失败时按错误类型执行软回滚、硬回滚或语义回滚，再选择重试、局部重规划或全局重规划。为了让系统不断进化，我会把失败轨迹沉淀为经验库，并用线上评估指标驱动路由和策略迭代。这样才能在真实生产中同时兼顾成功率、成本和稳定性。

### 知识扩展

- LangGraph：提供条件边和状态传递机制，是实现回滚和重规划的天然载体。
- Guardrails：约束校验器决定“何时回滚”和“何时提交”，与 Self-Correction 强耦合。
- Evals Pipeline：离线回放 + 在线指标是 Agent 进化的核心基础设施。
- Memory System：回滚后是否保留事实依赖记忆分层设计，避免污染长期记忆。
- Human-in-the-loop：高风险场景下的人类审批节点是最终安全阀。

## 2.9 一般情况下 Agent 的响应时间是多少？各个环节耗时通常是多少？如何优化？

如果面试官问“Agent 的响应时间一般是多少”，最稳妥的回答不是给一个绝对值，而是先讲清楚它是由多个阶段叠加出来的。对于在线交互型 Agent，常见的端到端响应时间通常在 1s ~ 5s 左右；如果只做简单问答、命中缓存或不调用外部工具，可能可以压到几百毫秒；如果涉及多轮规划、多次工具调用或重型 RAG 检索，整体延迟到 5s 以上也很常见。

### 一、先拆分 Agent 的耗时结构

一个典型 Agent 的总耗时可以写成：

$$
T_{total} = T_{pre} + T_{retrieval} + T_{llm} + T_{tool} + T_{post}
$$

其中：

- $T_{pre}$：输入预处理、路由、记忆拼装、提示词构建。
- $T_{retrieval}$：RAG 检索、rerank、上下文压缩。
- $T_{llm}$：LLM 推理和生成。
- $T_{tool}$：外部工具调用、数据库查询、HTTP 请求。
- $T_{post}$：结果校验、格式化、回填记忆、日志上报。

### 二、各环节通常耗时多少

#### 1. LLM 推理 (通常是最大头)

- 小模型或短上下文：约 100ms ~ 500ms。
- 中等模型、常规对话：约 500ms ~ 2s。
- 大模型、长上下文或复杂推理：约 2s ~ 10s 以上。

LLM 的耗时通常受以下因素影响最大：

1. 模型参数量和推理框架。
2. 输入上下文长度。
3. 输出 token 数。
4. 是否需要多轮思考、反思或多次重写。

#### 2. Tool 调用

工具调用的耗时波动最大，因为它取决于外部系统：

- 本地纯函数、内存计算：通常 < 10ms。
- 本地数据库查询：约 10ms ~ 100ms。
- 内网 HTTP / RPC：约 50ms ~ 500ms。
- 外部第三方 API：约 200ms ~ 3s，甚至更高。

如果 Agent 串行调用多个工具，Tool 阶段往往会成为主要延迟来源之一。

#### 3. RAG 检索

RAG 检索通常分成召回和精排两部分：

- 向量召回：约 10ms ~ 100ms。
- 混合检索 + rerank：约 50ms ~ 300ms。
- 如果候选集很大、文档很长或 reranker 较重，可能到 500ms 以上。

RAG 的核心不是“最慢”，而是“容易在高 K、长 chunk、重 rerank 下显著放大延迟”。

#### 4. 预处理和后处理

- Prompt 组装、记忆压缩、结构化解析：通常 10ms ~ 100ms。
- 输出校验、JSON 修复、格式化：通常 5ms ~ 50ms。

### 三、典型场景下的粗略体感

可以用经验值来回答：

1. 简单 Agent (无工具、短回答)：约 300ms ~ 1s。
2. 标准 RAG Agent (1 次检索 + 1 次生成)：约 1s ~ 3s。
3. 带工具调用的 Agent (检索 + 1~3 次工具)：约 2s ~ 6s。
4. 复杂规划型 Agent (多轮反思、多工具、多步执行)：约 5s ~ 20s 甚至更久。

真正线上体验上，通常更关注 P50 / P95 延迟，而不是平均值，因为 Agent 的尾延迟往往更能反映用户体验。

### 四、如何优化 Agent 响应时间

#### 1. 缓存 (Cache)

缓存是最直接的降延迟手段，通常分为几层：

- Prompt 缓存：相同系统提示词、模板片段直接复用。
- Retrieval 缓存：相同 Query 或相似 Query 的检索结果缓存。
- Tool 缓存：相同参数的工具调用结果缓存。
- Memory 缓存：近期对话摘要、用户画像、常用事实缓存。

缓存的价值不是只省时间，还能稳定 P95 延迟。

#### 2. 并行 (Parallelism)

能并行就不要串行，常见并行点包括：

- 多路检索并行 (BM25 + 向量 + 关键词)。
- 多个工具并行调用 (比如同时查库存、查订单、查配置)。
- 检索和部分预处理并行 (如一边做记忆压缩，一边做向量召回)。

并行的收益通常比单纯优化单点模型更明显，但要注意最终还要做结果融合和去重。

#### 3. 流式输出 (Streaming)

流式输出不一定降低总耗时，但能显著降低用户感知延迟。

- 首 token 尽快返回，让用户尽早看到响应。
- 长回答边生成边展示，避免“卡住不动”的感觉。
- 对于需要工具调用的 Agent，可以先返回中间进度，例如“正在检索资料”“正在调用数据库”。

这在交互体验上非常关键，尤其适合面向人类用户的产品。

#### 4. 降低单轮复杂度

- 缩短上下文，只保留必要消息和高价值记忆。
- 控制 chunk size 和 rerank 候选数。
- 减少不必要的反思轮次和工具链长度。
- 将复杂任务拆成“先快后慢”的两阶段：先给粗答，再补充细节。

#### 5. 早停和分级返回

- 对简单问题直接走快速路径，不必进入完整 Agent 循环。
- 对高延迟工具设置超时和降级。
- 当置信度足够时提前结束，不做额外推理。

### 五、一个可操作的延迟优化思路

可以把 Agent 设计成“快路径 + 慢路径”：

```text
用户输入
-> 路由判断
-> 快路径：缓存命中 / 简单问答 / 直接生成
-> 慢路径：RAG / 工具调用 / 多轮规划
-> 流式返回 + 后续补充
```

这样对多数简单请求可以控制在 1s 内，而复杂请求则通过更强能力换取更高质量。

### 六、常见误区

1. 误区：只优化 LLM 就够了。
    实际上很多 Agent 的慢点在检索、工具和串行调度。
2. 误区：平均延迟好看就行。
    用户更敏感的是 P95 和首 token 时间。
3. 误区：并行越多越好。
    并行会引入融合成本、冲突消解和资源竞争。
4. 误区：流式输出能减少总耗时。
    它更多是改善感知延迟，不是减少真实计算耗时。

### 七、面试可直接复述的总结

可以这样回答：Agent 的响应时间没有一个固定值，通常要按链路拆开看。简单 Agent 可能在几百毫秒到 1 秒，标准 RAG Agent 通常在 1 到 3 秒，带多次工具调用或复杂规划的 Agent 往往在 5 秒以上。整体耗时主要由 LLM 推理、Tool 调用和 RAG 检索构成，其中 LLM 往往是主耗时，但外部工具和重检索也可能成为瓶颈。优化上我会优先做缓存、并行和流式输出，再配合缩短上下文、减少工具链长度和早停策略，从而同时控制真实延迟和用户感知延迟。

### 知识扩展

- P95 / P99 延迟：比平均值更能反映 Agent 在生产中的尾部体验。
- Speculative Decoding：可用于降低 LLM 首 token 和生成延迟。
- Request Routing：先分流简单问题和复杂问题，是控制延迟的关键前置能力。
- Observability：需要把 LLM、RAG、Tool 三段延迟分别打点，才能定位真正瓶颈。
- Cost Control：延迟优化通常和 Token 成本、工具成本一起联动设计。

## 2.10 Skill 是什么？讲得越具体越透彻越好

如果把 Agent 系统类比成一个操作系统，那么 Skill 更像是“可复用的原子能力包”。它不是单次对话里的临时提示词，也不是笼统的工具集合，而是把某一类任务所需的知识、动作、约束、输入输出协议和质量标准封装成一个稳定模块，供上层 Agent 或 Workflow 直接调用。

一句话理解：Skill = 面向特定任务域的“标准化能力单元”，它介于 Prompt、Tool、Workflow 之间，负责把一个可重复的任务能力产品化。

### 一、Skill 的核心定位

Skill 的本质不是“会一点这个任务”，而是“能稳定完成这类任务”。它通常具备以下特征：

1. 任务聚焦：只解决一个明确场景，比如代码审查、文档总结、SQL 生成、网页检索。
2. 输入约束明确：知道自己接收什么类型的上下文、参数和环境信息。
3. 输出格式固定：会输出结构化结果、明确结论或标准化中间产物。
4. 可组合：可以被 Agent、Workflow 或更大的 Skill 再次调用。
5. 可评估：可以通过离线样例和线上指标验证质量。

### 二、Skill 与相关概念的区别

#### 1. Skill 和 Prompt 的区别

- Prompt 是一次性的语言指令，偏“告诉模型怎么想”。
- Skill 是可复用的能力封装，偏“把一类任务的执行方式固化下来”。

如果只用 Prompt，往往每次都要重新组织上下文；如果沉淀成 Skill，就可以把提示词、规则、模板、检索逻辑和校验逻辑统一管理。

#### 2. Skill 和 Tool 的区别

- Tool 是执行动作的“手”，比如搜索、计算、读写文件、调用 API。
- Skill 是解决问题的方法论和流程编排，通常会调用多个 Tool。

可以理解为：Tool 负责“做”，Skill 负责“怎么做、先做什么、后做什么、做到什么标准”。

#### 3. Skill 和 Workflow 的区别

- Workflow 更像任务流编排，强调步骤顺序和状态流转。
- Skill 更像能力模块，强调某一类任务的专业处理方式。

Workflow 可以调用多个 Skill；Skill 也可以内部包含一个小型 Workflow。

#### 4. Skill 和 Agent 的区别

- Agent 是会决策的系统，负责判断下一步做什么。
- Skill 是被决策系统调用的执行能力单元。

Agent 往往拥有多个 Skill，并根据任务自动选择；Skill 本身通常不负责全局规划。

### 三、一个 Skill 通常包含哪些组成部分

一个工程上可落地的 Skill，通常不只是“一个 prompt 文件”，而是一套能力包，常见包括：

1. 目标定义：这个 Skill 解决什么问题，不解决什么问题。
2. 适用边界：输入前提、依赖条件、禁用场景。
3. 处理流程：任务拆解、检索、推理、调用工具、校验。
4. 提示模板：系统提示词、角色定义、few-shot 示例。
5. 工具编排：需要调用哪些 Tool，调用顺序如何。
6. 输出协议：返回 JSON、Markdown、代码、表格还是自然语言。
7. 质量标准：正确性、覆盖率、格式合法性、可解释性。
8. 回退策略：失败时如何降级、重试或切换其他 Skill。

### 四、Skill 的典型设计模式

#### 1. 单一职责 Skill

只处理一个非常明确的任务，例如：

- `sql-generator`
- `code-review`
- `meeting-summary`
- `doc-search`

这种 Skill 最容易维护，也最容易评估。

#### 2. 分层 Skill

上层 Skill 负责任务分解，下层 Skill 负责具体执行。例如：

- `research-skill`：先找资料、筛选证据。
- `writing-skill`：再根据证据输出成文。
- `verification-skill`：最后做一致性检查。

#### 3. 组合式 Skill

一个复杂任务通常不是单个 Skill 完成，而是多个 Skill 串联。例如技术方案生成可以拆成：

- 需求解析 Skill
- 资料检索 Skill
- 方案生成 Skill
- 风险审查 Skill
- 格式化输出 Skill

### 五、Skill 的生命周期

一个成熟 Skill 不是写完就结束，而是要经历完整生命周期：

1. 需求定义：明确任务边界和成功标准。
2. 设计实现：定义 prompt、工具、输出协议和约束。
3. 测试评估：用 benchmark、回放样例和人工审查验证。
4. 上线观测：监控成功率、耗时、失败类型、用户反馈。
5. 持续迭代：根据错误样本更新提示词、规则和工具链。

### 六、Skill 在工程上怎么落地

常见落地方式有三种：

#### 1. Prompt + Metadata

把 Skill 定义成一个带元数据的提示模板，例如：

```json
{
  "name": "code-review",
  "description": "对代码变更进行结构化审查",
  "input_schema": {
     "diff": "string",
     "language": "string"
  },
  "output_schema": {
     "findings": "array",
     "risk_level": "string"
  },
  "prompt_template": "请基于以下 diff 做代码审查..."
}
```

这种方式简单直接，适合轻量 Skill。

#### 2. Skill + Tool Chain

Skill 先调用检索、解析、计算、验证等 Tool，再把结果组织成最终答案。它更像“半自动专家流程”。

#### 3. Skill as a Service

把 Skill 当作独立服务或插件，对外暴露统一 API，供多个 Agent 复用。这样便于版本管理、权限控制和灰度发布。

### 七、Skill 设计时最重要的原则

1. 任务边界要窄。
    越窄越容易稳定，越容易评测。
2. 输出要标准化。
    能 JSON 就不要纯自然语言，能结构化就不要混格式。
3. 失败要可降级。
    不能让 Skill 失败直接拖垮整个 Agent。
4. 能复用就不要重复造轮子。
    让 Skill 变成组织级能力资产，而不是散落在 prompt 里的临时代码。

### 八、与 engine / sub engine / MCP / Agent / Workflow 的关系

可以这样理解它们的层次：

```text
Agent / Workflow (负责决策与编排)
     └── Skill (负责某类任务的标准化能力)
             └── Tool / MCP Server (负责具体动作和外部能力接入)
```

- `engine`：通常是更上层的运行时或执行框架，负责调度和容器化承载。
- `sub engine`：把复杂任务再拆一层，承载局部子流程或子能力。
- `skill`：面向任务域的能力模块。
- `mcp`：更多是标准化工具接入协议，让 Skill 可以稳定调用外部能力。

如果再往实现上看，Skill 往往是“让 Agent 真正变聪明”的关键中间层，因为它把通用模型能力转成了业务可控、可复用、可评估的专业能力。

### 九、常见误区

1. 误区：Skill 就是一个长 Prompt。
    不对。真正的 Skill 至少应该包含边界、协议、工具链和质量标准。
2. 误区：Skill 越大越强。
    过大的 Skill 往往职责不清，反而难维护、难评测。
3. 误区：Skill 只要能跑就行。
    没有评测和版本管理的 Skill 很快会失控。
4. 误区：Skill 和 Agent 是同一层概念。
    Agent 负责决策，Skill 负责具体能力，两者不是一个维度。

### 十、面试可直接复述的总结

可以这样回答：Skill 是一种面向特定任务域的标准化能力单元，它不是一次性的 Prompt，也不是单纯的 Tool，而是把任务目标、输入输出协议、处理流程、工具调用和质量标准封装起来，供 Agent 或 Workflow 复用。Skill 的价值在于把通用模型能力产品化、模块化和可评估化，让系统具备可复用、可治理、可迭代的专业能力。工程上我会把 Skill 设计成边界清晰、输出标准、失败可降级的模块，并通过元数据、工具链和版本管理来持续演进。

### 知识扩展

- Tool Calling：Skill 经常通过 Tool 完成具体动作，Tool 是 Skill 的执行层。
- Workflow Orchestration：多个 Skill 组合后通常需要工作流来协调顺序和状态。
- MCP：为 Skill 接入外部能力提供标准协议，降低集成成本。
- Agent Routing：Agent 负责选择调用哪个 Skill，是 Skill 上层的决策机制。
- Evaluation Framework：Skill 必须依赖离线 benchmark 和线上指标持续评估。

## 2.11 给出一个完整的 Skill 示例，包括这个 Skill 的目录结构以及这个 Skill 的具体执行过程

这个问题最能体现你是否真的做过 Skill 工程化。下面给一个可以直接落地的示例：我们定义一个 `code-review-skill`，目标是对代码变更进行结构化审查，并输出可执行的风险结论。

### 一、先定义 Skill 的目标和边界

#### 1. 目标

- 输入：代码 diff、语言类型、仓库上下文信息。
- 输出：结构化审查报告 (问题列表、严重级别、建议修复方案、是否阻断合并)。

#### 2. 非目标

- 不负责自动修复代码。
- 不负责执行单元测试。
- 不负责最终合并决策 (只提供建议)。

#### 3. 成功标准

- 漏报率可控。
- 输出格式稳定。
- 可追踪证据 (指出具体文件和代码片段)。

### 二、Skill 目录结构示例

下面是一个常见、可维护的目录布局：

```text
skills/
    code-review-skill/
        SKILL.md                    # 能力说明：目标、边界、输入输出、流程
        skill.yaml                  # 元数据：名称、版本、路由标签、依赖
        prompts/
            system.prompt.md          # 系统级审查准则
            reviewer.prompt.md        # 主审查提示词模板
            severity-rubric.prompt.md # 严重级别判定标准
        schemas/
            input.schema.json         # 输入校验
            output.schema.json        # 输出校验
        tools/
            tool_manifest.yaml        # 允许调用的工具白名单
        pipeline/
            nodes.yaml                # 节点定义 (parse -> analyze -> verify -> format)
            routing.yaml              # 分支规则 (按语言、变更规模路由)
        examples/
            sample_input.json
            sample_output.json
        tests/
            eval_cases.jsonl          # 回放样例集
            golden_set.jsonl          # 金标集
        scripts/
            run_local_eval.sh         # 本地评测脚本
```

这个结构的核心价值是把“提示词、工具、协议、测试”拆开治理，避免所有逻辑塞进一个长 prompt。

### 三、关键配置文件示例

#### 1. `skill.yaml` (元数据)

```yaml
name: code-review-skill
version: 1.3.0
description: 对代码变更进行结构化审查并输出风险结论
owner: ai-platform
entrypoint: pipeline/nodes.yaml
tags:
    - code-review
    - quality-gate
input_schema: schemas/input.schema.json
output_schema: schemas/output.schema.json
allowed_tools:
    - diff_parser
    - repo_search
    - lint_runner
    - test_signal_reader
sla:
    timeout_ms: 4000
    max_tool_calls: 4
fallback:
    on_timeout: return_partial
    on_schema_error: reformat_once
```

#### 2. `output.schema.json` (输出协议)

```json
{
    "type": "object",
    "required": ["summary", "risk_level", "findings", "merge_block"],
    "properties": {
        "summary": {"type": "string"},
        "risk_level": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
        "merge_block": {"type": "boolean"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["file", "severity", "issue", "suggestion", "evidence"],
                "properties": {
                    "file": {"type": "string"},
                    "severity": {"type": "string"},
                    "issue": {"type": "string"},
                    "suggestion": {"type": "string"},
                    "evidence": {"type": "string"}
                }
            }
        }
    }
}
```

这一步很关键：输出先协议化，后续才能做自动校验、自动评测和自动回归。

### 四、Skill 的具体执行过程 (端到端)

可以把执行分为 7 步：

1. `Input Validate`
     校验 diff、language、repo_id 是否满足 `input.schema.json`。
2. `Context Build`
     拼接代码变更、相关文件片段、历史缺陷规则。
3. `Tool Assist`
     调用 `diff_parser` 和 `repo_search` 抽取关键风险上下文。
4. `LLM Analyze`
     用 `reviewer.prompt.md` 生成初稿审查结果。
5. `Rule Verify`
     用 `severity-rubric.prompt.md` + 规则引擎重判严重级别。
6. `Schema Check`
     按 `output.schema.json` 校验，不合法则触发一次重格式化。
7. `Return + Log`
     返回结构化结果，并记录耗时、命中规则、失败原因。

流程图如下：

```text
请求进入
    -> 输入校验
    -> 构建上下文
    -> 工具抽取 (diff_parser/repo_search)
    -> LLM 审查
    -> 规则复核 (严重级别/阻断条件)
    -> 输出协议校验
    -> 返回结果 + 观测埋点
```

### 五、简化伪代码

```python
def run_code_review_skill(payload, toolset, llm, schema):
        validate_input(payload, schema.input)

        ctx = build_context(payload)
        parsed = toolset.diff_parser(payload["diff"])
        refs = toolset.repo_search(parsed["touched_symbols"])

        draft = llm.generate("reviewer.prompt.md", {
                "context": ctx,
                "parsed_diff": parsed,
                "references": refs
        })

        verified = apply_severity_rubric(draft)
        result = ensure_output_schema(verified, schema.output)

        if not result.valid:
                result = reformat_once_with_schema(llm, verified, schema.output)

        emit_metrics(result)
        return result.data
```

这段伪代码体现了 Skill 的工程核心：输入校验、工具增强、模型推理、规则复核、协议校验、可观测输出。

### 六、这个 Skill 在 Agent 体系中的调用方式

在上层 Agent 看来，Skill 只是一个能力节点：

- Router 判断用户请求是否属于“代码审查”意图。
- 命中后直接调用 `code-review-skill`。
- Skill 返回结构化报告。
- Agent 再决定是否继续调用“修复建议 Skill”或“测试执行 Skill”。

这说明 Skill 的价值不只是“回答问题”，而是把能力标准化，让 Agent 可以稳定编排。

### 七、常见失败场景与处理

1. 输入缺字段
     直接拒绝执行并返回标准错误码。
2. 工具超时
     走降级路径，返回“部分审查 + 不确定性提示”。
3. 输出不合规
     自动重格式化一次，仍失败则返回兜底模板。
4. 高风险误判
     触发二次复核节点 (规则引擎或人工审批)。

### 八、面试可直接复述的总结

可以这样回答：完整 Skill 不是一段 Prompt，而是一个可复用能力包。以代码审查 Skill 为例，我会把它拆成目录化资产：元数据配置、提示词模板、输入输出 schema、工具白名单、执行 pipeline、样例和评测集。执行时走输入校验、上下文构建、工具增强、LLM 推理、规则复核、输出校验和埋点上报。这样 Skill 就具备可复用、可治理、可评测、可迭代的工程属性，能被 Agent 稳定调用，而不是一次性“靠提示词碰运气”。

### 知识扩展

- Agent Routing：决定什么时候调用这个 Skill，影响整体成功率和延迟。
- Guardrails：输入输出 schema、规则复核本质上属于 Guardrails 体系。
- Observability：Skill 级别埋点是定位质量回退和延迟抖动的关键。
- Evaluation Pipeline：需要 golden set + 回放评测来做版本回归。
- Skill Versioning：版本化发布和灰度切换是多团队协作的基础能力。

## 2.12 什么是 A2A 协议？它和 MCP 协议的区别是什么？

这个问题本质上在考“你是否理解多 Agent 系统的协议分层”。一句话先讲结论：A2A (Agent-to-Agent) 解决的是“Agent 和 Agent 怎么协作”，MCP (Model Context Protocol) 解决的是“模型或 Agent 怎么标准化连接工具和外部上下文”。两者不是替代关系，而是可以叠加。

### 一、什么是 A2A 协议

A2A 协议可以理解为多 Agent 间的通信与协作协议。它关注的是：

1. 如何发现其他 Agent 的能力 (Capability Discovery)
2. 如何发起任务委托 (Task Delegation)
3. 如何传递上下文和中间结果 (Context Exchange)
4. 如何汇报进度和最终结果 (Progress / Result Reporting)
5. 如何处理失败、超时、重试和补偿 (Failure Handling)

在工程上，A2A 常见用于以下场景：

- 主 Agent 把子任务委托给专业 Agent (如检索 Agent、代码 Agent、审计 Agent)
- 跨团队 Agent 协作 (每个团队暴露一个能力 Agent)
- 长流程任务中的分布式并行处理

如果抽象成一个简单通信模型，可以写成：

$$
Request_{A\to B} = \{goal, context, constraints, deadline\}
$$

$$
Response_{B\to A} = \{status, artifacts, confidence, next\_actions\}
$$

这说明 A2A 的核心是“任务语义 + 协作状态”，而不只是函数调用。

### 二、什么是 MCP 协议

MCP (Model Context Protocol) 的核心是给模型或 Agent 提供统一的外部能力接入方式，包括：

- 工具调用 (Tools)
- 资源读取 (Resources)
- 统一上下文注入 (Context)

它解决的是“接入标准化”问题，让不同模型客户端可以用一致方式访问外部能力，而不用为每个工具做一套私有适配。

一句话理解：MCP 更像“模型到工具的标准 I/O 总线”。

### 三、A2A 和 MCP 的关键区别

#### 1. 交互对象不同

- A2A：Agent <-> Agent
- MCP：Model/Agent <-> Tool/Resource Server

#### 2. 关注点不同

- A2A 关注协作语义：任务分解、角色分工、状态流转、结果合并。
- MCP 关注能力接入：如何声明工具、如何调用、如何返回。

#### 3. 抽象层级不同

- A2A 是工作流和组织协作层。
- MCP 是工具与上下文接入层。

#### 4. 典型消息形态不同

- A2A 消息通常包含目标、约束、子任务状态、质量要求。
- MCP 消息通常包含工具参数、资源句柄、调用结果。

#### 5. 失败处理方式不同

- A2A 常见是任务级补偿 (重分配、回滚、降级、人工接管)。
- MCP 常见是调用级补偿 (重试、超时、参数修复、熔断)。

### 四、一个直观对比示例

假设你要做“自动生成技术方案并审校”的系统：

1. 主 Agent 将“检索资料”委托给 Research Agent。
2. 将“生成初稿”委托给 Writer Agent。
3. 将“合规审查”委托给 Review Agent。

以上是 A2A 层协作。

而每个 Agent 在执行时，会通过 MCP 去调用：

- 搜索工具
- 文档库资源
- 规范库 API

以上是 MCP 层接入。

可以画成：

```text
Orchestrator Agent
  -> (A2A) Research Agent
  -> (A2A) Writer Agent
  -> (A2A) Review Agent

Each Agent
  -> (MCP) search tool / db resource / policy api
```

### 五、二者如何组合使用

在生产系统里，推荐分层设计：

1. 上层用 A2A 做协作编排
    负责任务拆分、路由、状态机、重试与补偿。
2. 下层用 MCP 做能力接入
    负责工具标准化、资源访问、安全鉴权和可观测调用。

这样的好处是“协作逻辑”和“工具接入逻辑”解耦，系统更易扩展。

### 六、选型建议

1. 只做单 Agent + 多工具
    优先 MCP，不一定需要 A2A。
2. 多 Agent 协作明显
    必须引入 A2A 语义层，再配 MCP 接工具。
3. 要跨团队共享能力
    用 A2A 封装能力 Agent，用 MCP 统一底层工具访问。

### 七、常见误区

1. 误区：A2A 和 MCP 是竞争协议。
    不对，它们通常是上下层关系，协同使用。
2. 误区：有了 MCP 就天然有多 Agent 协作。
    不对，MCP 只解决接入标准，不解决任务编排。
3. 误区：A2A 只是“把 HTTP 接口互调”换个名字。
    不对，A2A 的重点是任务语义、状态和协作契约。
4. 误区：协议统一后就不需要治理。
    仍需做权限、配额、审计、超时和降级策略。

### 八、面试可直接复述的总结

可以这样回答：A2A 协议用于 Agent 与 Agent 之间的协作，核心是任务委托、状态流转和结果合并；MCP 协议用于模型或 Agent 对工具与外部资源的标准化接入，核心是统一调用接口。两者关注层级不同，A2A 偏协作编排，MCP 偏能力接入。在实际系统里我会采用“上层 A2A、下层 MCP”的分层架构，这样可以同时获得多 Agent 协作能力和统一工具生态。

### 知识扩展

- Multi-Agent Orchestration：A2A 的落地通常需要状态机和任务编排框架配合。
- Tool Governance：MCP 生态需要权限控制、审计日志和调用配额。
- Contract-First Design：A2A 与 MCP 都应先定义协议契约，再做实现。
- Observability：建议区分“协作链路指标”(A2A) 与“工具调用指标”(MCP)。
- Reliability Engineering：A2A 更关注任务级恢复，MCP 更关注调用级恢复。

## 2.13 分析一下 Agent 的路由优化问题：怎么让 Agent 在合适的场景采用合适的模型，做到既节约成本又不牺牲质量？

> Agent的成本优化，核心问题是任务难度和模型能力的不对称——80%的请求是简单任务，用大模型是浪费。我的解法是三层路由：高频简单场景用规则拦截，零成本零延迟；模糊地带用路由模型做难度评分，按分选模型；不确定的一律走大模型兜底，保质量底线。路由模型的训练，我倾向于用评分器而不是分类器，因为难度分比模型名更稳定，新增模型时只需要调阈值。冷启动阶段用大模型置信度当难度标签的代理，渐进放大小模型比例。级联降级（小模型先试、不行再升级）看似合理，但复杂请求会被小模型白试一次，既浪费成本又增加延迟。对质量和延迟有要求的场景，先路由再选模型比先试再升级更优。"这个回答从问题本质讲到方案设计，再指出级联降级的坑，比只背"用小模型省钱"高一档。

这是一个非常实战的工程问题。面试时先给结论：路由优化的本质不是"用小模型替代大模型"，而是"让系统有能力判断任务复杂度，并把任务分发到成本最合理的执行路径上"。核心思路是 **分级处理 + 质量兜底**。

一句话总结：**路由优化 = 任务复杂度评估 + 分级执行策略 + 质量监控闭环**，目标是在整体成本可控的前提下，让简单任务不浪费算力、复杂任务不缺能力。

### 一、为什么需要路由优化

#### 1. 成本现实

以 GPT-4o 与 GPT-4o-mini 为例：

| 模型              | 输入价格 (per 1M tokens) | 输出价格 (per 1M tokens) | 典型延迟      |
| ----------------- | ------------------------ | ------------------------ | ------------- |
| GPT-4o            | $2.50                    | $10.00                   | 500ms ~ 2s    |
| GPT-4o-mini       | $0.15                    | $0.60                    | 100ms ~ 500ms |
| Claude 3.5 Sonnet | $3.00                    | $15.00                   | 500ms ~ 2s    |
| 本地 7B 模型      | 硬件成本 (固定)          | 硬件成本 (固定)          | 50ms ~ 200ms  |

价格差距可以达到 **10~60 倍**。如果所有请求都走最贵的模型，成本会快速失控。

#### 2. 质量现实

但不能简单地"全用小模型"。小模型在以下场景质量明显下降：

- 复杂推理、数学证明、多步逻辑
- 长上下文理解和信息整合
- 精细的指令遵循和格式控制
- 多语言、小语种处理
- 代码生成和 Debug

所以路由优化的核心矛盾是：**简单任务用大模型是浪费，复杂任务用小模型会翻车**。

#### 3. 路由优化的目标

$$
\min_{router} \quad C_{total} = \sum_{i} c(model_i) \cdot n_i
$$

$$
\text{s.t.} \quad Q_{avg} \geq Q_{threshold}
$$

即在保证平均质量不低于阈值的前提下，最小化总成本。这是一个典型的约束优化问题。

### 二、路由决策需要看哪些维度

#### 1. 查询复杂度特征

```python
complexity_features = {
    "token_count": len(query.split()),              # 查询长度
    "semantic_complexity": estimate_semantic(query), # 语义复杂度
    "reasoning_required": detect_reasoning(query),   # 是否需要推理
    "domain_specificity": detect_domain(query),      # 领域专业度
    "multi_hop": detect_multi_hop(query),            # 是否需要多跳
    "format_constraint": detect_format(query),       # 格式约束强度
    "language": detect_language(query),              # 语言难度
}
```

#### 2. 上下文特征

```python
context_features = {
    "history_length": len(history),        # 对话轮数
    "rag_chunks_count": len(rag_chunks),   # 检索到的文档数
    "rag_chunks_length": sum_len(chunks),  # 检索文档总长度
    "tool_count": len(available_tools),    # 可用工具数
    "has_images": bool(images),            # 是否有图片
}
```

#### 3. 业务约束

```python
business_constraints = {
    "latency_budget_ms": 3000,         # 延迟预算
    "cost_budget_per_query": 0.01,     # 单次查询成本预算
    "quality_tier": "high",            # 质量等级要求
    "user_tier": "premium",            # 用户等级 (影响 SLA)
}
```

### 三、主流路由策略

#### 策略一：基于规则的静态路由

最简单直接的方式，用预设规则做分流：

```python
class RuleBasedRouter:
    """基于规则的静态路由器"""

    def __init__(self):
        self.rules = [
            # (条件, 目标模型)
            (lambda q: len(q) < 50 and not has_code(q), "gpt-4o-mini"),
            (lambda q: "翻译" in q or "translate" in q.lower(), "gpt-4o-mini"),
            (lambda q: "代码" in q or "bug" in q.lower(), "gpt-4o"),
            (lambda q: len(q) > 500, "gpt-4o"),
            (lambda q: "分析" in q and "推理" in q, "gpt-4o"),
        ]

    def route(self, query: str) -> str:
        for condition, model in self.rules:
            if condition(query):
                return model
        return "gpt-4o-mini"  # 默认走便宜模型
```

**优点**：实现简单、可解释、延迟极低 (微秒级)。

**缺点**：规则维护成本高，覆盖不全，无法泛化到未见过的查询模式。

#### 策略二：基于分类器的学习路由 (主流方案)

训练一个小分类器来判断查询复杂度，然后路由到对应模型：

```python
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

class LearnedRouter:
    """
    基于小模型的学习路由器
    用一个 < 1B 参数的小模型来判断查询应该路由到哪个大模型
    """

    def __init__(self, router_model_path: str):
        self.tokenizer = AutoTokenizer.from_pretrained(router_model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            router_model_path,
            num_labels=3  # simple / medium / complex
        )
        self.model.eval()
        self.label_to_model = {
            0: "gpt-4o-mini",     # simple
            1: "gpt-4o-mini",     # medium (小模型能处理)
            2: "gpt-4o",          # complex (需要大模型)
        }

    def route(self, query: str) -> str:
        inputs = self.tokenizer(
            query, return_tensors="pt",
            truncation=True, max_length=256
        )
        with torch.no_grad():
            logits = self.model(**inputs).logits
            label = torch.argmax(logits, dim=-1).item()
        return self.label_to_model[label]
```

**路由分类器的训练数据从哪来？**

```python
# 方法一：用大模型做 Teacher 标注
def generate_routing_labels(queries, strong_model, weak_model):
    """
    对每个 query 分别用强弱模型回答，
    如果弱模型的答案质量足够好 -> simple
    如果弱模型答案不行但强模型可以 -> complex
    """
    labels = []
    for q in queries:
        answer_weak = weak_model.generate(q)
        answer_strong = strong_model.generate(q)
        score_weak = evaluate_quality(q, answer_weak)
        score_strong = evaluate_quality(q, answer_strong)

        if score_weak >= 0.8:  # 弱模型够用
            labels.append(0)  # simple
        elif score_strong >= 0.8 and score_weak < 0.6:
            labels.append(2)  # complex
        else:
            labels.append(1)  # medium
    return labels

# 方法二：基于历史用户反馈
def labels_from_feedback(history):
    """从线上反馈中提取路由标签"""
    # 如果用小模型回答后用户满意度高 -> simple
    # 如果用小模型回答后用户追问/投诉 -> 需要升级
    pass
```

**优点**：可泛化、可在线学习迭代、路由延迟低 (小模型推理 ~10ms)。

**缺点**：需要训练数据、分类器本身也有误差。

#### 策略三：级联策略 (Cascade / Fallback)

先用便宜模型回答，如果质量不达标再升级到贵模型：

```python
class CascadeRouter:
    """
    级联路由：先便宜后贵，质量不达标就升级
    这是最实用的策略之一
    """

    def __init__(self, models, quality_threshold=0.7):
        # 按成本从低到高排列
        self.models = models  # [("gpt-4o-mini", 0.15), ("gpt-4o", 2.5)]
        self.quality_threshold = quality_threshold

    def route(self, query: str) -> str:
        for model_name, cost in self.models:
            answer = call_model(model_name, query)
            confidence = self._estimate_confidence(query, answer)

            if confidence >= self.quality_threshold:
                return answer  # 质量达标，直接返回

            # 质量不达标，继续尝试下一个更贵的模型
            print(f"[Cascade] {model_name} confidence={confidence:.2f}, escalating...")

        # 所有模型都不行，返回最贵模型的答案
        return answer

    def _estimate_confidence(self, query, answer) -> float:
        """
        置信度评估，可以用多种方式实现：
        1. Log probability (模型输出的 logprobs)
        2. Self-evaluation (让模型自评)
        3. 轻量级判别模型
        """
        # 方法一：基于 logprobs
        avg_logprob = compute_avg_logprob(answer)
        if avg_logprob > -0.5:
            return 0.9
        elif avg_logprob > -1.5:
            return 0.7
        else:
            return 0.4
```

**级联策略的核心是置信度评估**。常用的置信度信号：

```plaintext
┌──────────────────────────────────────────────────────┐
│              置信度评估信号                            │
│                                                      │
│  1. Log Probability                                  │
│     - 模型输出的 token 平均 logprob                   │
│     - logprob 越高 → 模型越"确定"                     │
│     - 优点: 无需额外调用                              │
│     - 缺点: 校准不一定准确                            │
│                                                      │
│  2. Self-Evaluation                                  │
│     - 让模型自己评估答案质量                          │
│     - "请评估以下回答的质量 (1-10)"                   │
│     - 优点: 语义层面评估                              │
│     - 缺点: 多一次 LLM 调用，成本翻倍                 │
│                                                      │
│  3. Entropy / Perplexity                             │
│     - 输出分布的熵越高 → 模型越不确定                 │
│     - 可以在多个采样中检查一致性                      │
│     - 优点: 统计上可靠                                │
│     - 缺点: 需要多次采样，延迟高                      │
│                                                      │
│  4. Lightweight Judge Model                          │
│     - 用一个专门训练的小判别模型                      │
│     - 输入 (query, answer)，输出质量分                │
│     - 优点: 专门优化，准确度高                        │
│     - 缺点: 需要额外训练和部署                        │
└──────────────────────────────────────────────────────┘
```

**级联的成本分析**：

$$
C_{cascade} = C_{cheap} \cdot P_{pass} + (C_{cheap} + C_{expensive}) \cdot (1 - P_{pass})
$$

其中 $P_{pass}$ 是便宜模型通过质量检查的概率。如果 $P_{pass} = 0.7$ (70% 的查询小模型能处理)，则：

$$
C_{cascade} = 0.15 \times 0.7 + (0.15 + 2.5) \times 0.3 = 0.105 + 0.795 = 0.90
$$

对比全用 GPT-4o 的 $C = 2.5$，节省了 **64%**。

#### 策略四：MoE 风格的混合路由

借鉴 Mixture of Experts 的思想，让多个模型"竞争"回答：

```python
class MoERouter:
    """
    MoE 风格的路由：
    根据输入特征计算每个模型的"适配分数"，
    选择最高分的模型执行
    """

    def __init__(self, models: dict, cost_weights: dict):
        self.models = models
        self.cost_weights = cost_weights  # 各模型的成本权重

    def route(self, query: str, context: dict) -> str:
        # 计算每个模型的综合得分
        scores = {}
        for model_name in self.models:
            quality_score = self._predict_quality(model_name, query, context)
            cost_score = 1.0 - self.cost_weights[model_name]  # 越便宜分越高
            latency_score = self._predict_latency(model_name, context)

            # 综合得分 = 质量权重 * 质量分 + 成本权重 * 成本分
            scores[model_name] = (
                0.6 * quality_score +
                0.3 * cost_score +
                0.1 * latency_score
            )

        return max(scores, key=scores.get)
```

#### 策略五：任务类型路由 (Task-Level Routing)

不同任务类型天然对应不同的最优模型：

```python
class TaskTypeRouter:
    """
    按任务类型路由，不同类型任务走不同模型
    """

    TASK_MODEL_MAP = {
        # 简单任务 → 便宜模型
        "greeting": "gpt-4o-mini",
        "translation": "gpt-4o-mini",
        "simple_qa": "gpt-4o-mini",
        "format_conversion": "gpt-4o-mini",
        "summarization": "gpt-4o-mini",

        # 中等任务 → 中等模型
        "rag_qa": "gpt-4o-mini",
        "code_review": "gpt-4o",
        "data_analysis": "gpt-4o",

        # 复杂任务 → 最强模型
        "complex_reasoning": "gpt-4o",
        "math_proof": "gpt-4o",
        "multi_step_planning": "gpt-4o",
        "creative_writing": "gpt-4o",
    }

    def __init__(self):
        self.classifier = TaskClassifier()  # 用小模型做任务分类

    def route(self, query: str, context: dict) -> str:
        task_type = self.classifier.classify(query, context)
        return self.TASK_MODEL_MAP.get(task_type, "gpt-4o-mini")
```

### 四、一个完整的生产级路由系统

在实际生产中，通常是多种策略组合使用：

```python
class ProductionRouter:
    """
    生产级路由器：多层决策 + 质量兜底
    """

    def __init__(self):
        self.rule_engine = RuleEngine()           # 规则层
        self.complexity_classifier = load_model() # 复杂度分类器
        self.cascade_checker = CascadeChecker()   # 级联质量检查
        self.cost_tracker = CostTracker()          # 成本追踪

    def route(self, query: str, context: dict) -> ModelResponse:
        # 第一层：硬规则拦截
        # 简单问候、格式转换等直接走最便宜的模型
        if self.rule_engine.can_handle(query):
            model = self.rule_engine.select_model(query)
            return self._execute(model, query, context)

        # 第二层：复杂度分类
        complexity = self.complexity_classifier.predict(query, context)

        if complexity == "simple":
            # 第三层：级联质量验证
            response = self._execute("gpt-4o-mini", query, context)
            if self.cascade_checker.is_quality_ok(response):
                return response
            # 质量不达标，升级
            return self._execute("gpt-4o", query, context)

        elif complexity == "medium":
            return self._execute("gpt-4o-mini", query, context)

        else:  # complex
            return self._execute("gpt-4o", query, context)

    def _execute(self, model, query, context):
        response = call_model(model, query, context)
        self.cost_tracker.record(model, query, response)
        return response
```

整体架构可以画成：

```text
用户 Query
    │
    ▼
┌──────────────────────┐
│ 第一层：硬规则拦截     │  → greeting/format → gpt-4o-mini
└──────────┬───────────┘
           │ 未命中
           ▼
┌──────────────────────┐
│ 第二层：复杂度分类器   │  → simple / medium / complex
└──────────┬───────────┘
           │
     ┌─────┼──────────┐
     ▼     ▼          ▼
  simple medium    complex
     │     │          │
     ▼     ▼          ▼
  mini   mini        4o
     │
     ▼
┌──────────────────────┐
│ 第三层：质量检查       │  → 不达标则升级到 4o
└──────────────────────┘
     │
     ▼
  返回结果 + 记录成本
```

### 五、路由效果的监控与持续优化

路由系统上线后，需要持续监控和迭代：

#### 1. 核心监控指标

```python
routing_metrics = {
    # 效果指标
    "quality_score_avg": 0.0,         # 平均答案质量
    "quality_score_by_model": {},     # 各模型的质量分
    "user_satisfaction_rate": 0.0,    # 用户满意度

    # 成本指标
    "avg_cost_per_query": 0.0,        # 单次查询平均成本
    "cost_saving_rate": 0.0,          # 相比全用大模型的成本节省率
    "model_usage_distribution": {},   # 各模型使用比例

    # 路由指标
    "escalation_rate": 0.0,           # 级联升级比例
    "routing_accuracy": 0.0,          # 路由决策准确率
    "router_latency_ms": 0.0,         # 路由决策耗时
}
```

#### 2. A/B 测试框架

```python
class RoutingABTest:
    """
    路由策略 A/B 测试
    """

    def __init__(self, strategy_a, strategy_b, split_ratio=0.5):
        self.strategy_a = strategy_a
        self.strategy_b = strategy_b
        self.split_ratio = split_ratio
        self.results_a = []
        self.results_b = []

    def route(self, query: str, context: dict):
        if hash(query) % 100 < self.split_ratio * 100:
            result = self.strategy_a.route(query, context)
            self.results_a.append(result)
        else:
            result = self.strategy_b.route(query, context)
            self.results_b.append(result)
        return result

    def evaluate(self):
        """评估两个策略的效果差异"""
        quality_a = avg_quality(self.results_a)
        quality_b = avg_quality(self.results_b)
        cost_a = avg_cost(self.results_a)
        cost_b = avg_cost(self.results_b)

        return {
            "quality_diff": quality_a - quality_b,
            "cost_diff": cost_a - cost_b,
            "recommendation": "A" if quality_a >= quality_b and cost_a <= cost_b else "B"
        }
```

#### 3. 路由决策的离线回放与校准

```python
def recalibrate_router(router, new_data):
    """
    定期用新数据重新校准路由器
    """
    # 1. 用新数据重新评估路由决策
    decisions = []
    for query, ground_truth_answer in new_data:
        routed_model = router.route(query)
        actual_answer = call_model(routed_model, query)
        quality = evaluate_quality(query, actual_answer, ground_truth_answer)
        decisions.append((query, routed_model, quality))

    # 2. 找出路由错误的案例
    misrouted = [
        (q, m, q_score)
        for q, m, q_score in decisions
        if q_score < QUALITY_THRESHOLD
    ]

    # 3. 用错误案例更新分类器
    if len(misrouted) > MIN_RETRAIN_SAMPLES:
        retrain_classifier(router.classifier, misrouted)
```

### 六、进阶：端到端的路由优化 (Router Tuning)

可以把路由策略本身也纳入优化目标，用强化学习或 bandit 方法来学习最优路由：

$$
\pi^* = \arg\max_{\pi} \mathbb{E}_{q \sim D} \left[ \alpha \cdot Q(q, \pi(q)) - \beta \cdot C(\pi(q)) \right]
$$

其中 $\pi(q)$ 是路由器对查询 $q$ 的模型选择，$Q$ 是质量评分，$C$ 是成本，$\alpha$ 和 $\beta$ 是平衡超参。

可以用 Contextual Bandit 实现：

```python
class BanditRouter:
    """
    基于 Contextual Bandit 的自适应路由器
    """

    def __init__(self, models, alpha=0.7, beta=0.3):
        self.models = models
        self.alpha = alpha  # 质量权重
        self.beta = beta    # 成本权重
        self.history = []

    def select_model(self, features: dict) -> str:
        # 计算每个模型的期望奖励
        rewards = {}
        for model in self.models:
            expected_quality = self._predict_quality(model, features)
            expected_cost = self._get_cost(model)

            reward = self.alpha * expected_quality - self.beta * expected_cost
            rewards[model] = reward

        # Epsilon-greedy: 大部分选最优，小部分探索
        if random.random() < 0.05:  # 5% 探索
            return random.choice(self.models)
        return max(rewards, key=rewards.get)

    def update(self, features, model, quality, cost):
        """收到反馈后更新模型"""
        self.history.append((features, model, quality, cost))
        self._retrain_predictor()
```

### 七、常见误区

1. 误区：路由优化就是用便宜模型。
    不对，核心是"用合适的模型"。有时最贵的模型反而是最划算的 (如果能一次做对)。

2. 误区：有了路由就不需要质量监控。
    路由器本身也有误差，必须有质量兜底机制 (如级联升级)。

3. 误区：路由分类器越复杂越好。
    路由器本身的推理延迟和成本也要考虑。如果路由器比大模型还慢，就本末倒置了。

4. 误区：只看成本不看延迟。
    便宜模型往往也更快。延迟优化和成本优化经常是同向的。

5. 误区：路由策略一劳永逸。
    业务场景变化、模型更新换代、用户行为变化都会影响路由效果，需要持续校准。

6. 误区：所有请求都应该走路由器。
    极高 SLA 要求的请求可能需要直接走最可靠的模型，跳过路由判断。

### 八、面试可直接复述的总结

可以这样回答：Agent 路由优化的核心是"让合适的任务走合适的模型"。我会采用多层路由策略：第一层用硬规则拦截简单任务 (问候、格式转换等)，直接走轻量模型；第二层用一个轻量分类器判断查询复杂度，将查询分流到不同级别的模型；第三层用级联质量检查做兜底——如果小模型的回答置信度不达标，自动升级到大模型。训练数据可以用"大小模型对比法"自动生成：对同一个查询分别用强弱模型回答，弱模型够好就标为 simple，否则标为 complex。线上通过 A/B 测试持续校准路由策略，监控成本节省率和质量指标。如果场景更复杂，还可以引入 Contextual Bandit 做自适应路由，让系统在运行中自动学习最优分发策略。总体目标是在保证平均质量不低于阈值的前提下，尽可能降低单次查询成本。

### 知识扩展

- Mixture of Experts (MoE)：路由优化在模型层面就是 MoE 的思想——多个专家网络各有所长，路由器决定激活哪个专家。Agent 路由是 MoE 在系统层面的外延。
- Cascaded Inference：级联推理与投机解码 (Speculative Decoding) 有相似思想，都是先用小模型快速出结果，再决定是否需要更强模型修正。
- Adaptive RAG：RAG 中也有类似的路由思想——根据查询复杂度决定走 Naive RAG 还是 Advanced RAG 还是 Graph RAG。
- Reinforcement Learning from Human Feedback (RLHF)：路由策略的优化目标 (质量 vs 成本) 可以用 RLHF 的框架来建模，把用户反馈作为 reward signal。
- Request Scheduling & Load Balancing：路由优化与系统层面的请求调度、负载均衡密切相关，需要考虑模型服务的并发能力和排队延迟。
- Token Budget Management：路由决策直接影响 token 预算分配，与上下文管理、记忆压缩等技术联动设计。
- Model Evaluation & Benchmarking：路由策略的有效性依赖于对各模型在各任务上质量的准确评估，与模型评测体系强相关。

## 2.14 如果让你设计一个 Agent 编程工具，你会怎么设计安全机制？

> Agent 编程工具的安全问题本质是：LLM 生成的代码可以访问文件系统、网络和操作系统，而模型本身不可信、上下文可被注入、用户意图可能被曲解。我的安全设计核心是三层防线：第一层是**沙箱隔离**，所有代码执行必须在容器或虚拟机中完成，限制文件系统、网络和系统调用的范围；第二层是**权限最小化**，每个 Tool 只暴露完成任务所需的最少操作，敏感操作必须二次确认；第三层是**输入输出审计**，对 LLM 的指令做静态分析和动态检测，拦截 prompt injection、路径遍历、数据泄露等攻击。同时引入"人在回路"机制：高危操作 (删除文件、推送代码、修改配置) 需要用户显式批准，而不是自动执行。这个回答从威胁模型出发，讲到分层防御，再到人机协作兜底，体现了对安全工程的系统性思考。

Agent 编程工具 (如 Claude Code, Cursor, GitHub Copilot Workspace 等) 的安全挑战远比普通 LLM 应用复杂，因为它不只是"生成文本"，而是**生成并执行代码、操作文件系统、调用外部服务**。安全设计需要从威胁建模出发，分层防御。

一句话总结：**Agent 编程工具的安全 = 沙箱隔离 (限制执行环境) + 权限最小化 (限制操作范围) + 输入输出审计 (拦截恶意行为) + 人在回路 (高危操作兜底)**。

### 一、威胁模型分析

设计安全机制之前，必须先明确威胁来自哪里：

| 威胁类型         | 具体场景                                                           | 危害等级 |
| ---------------- | ------------------------------------------------------------------ | -------- |
| Prompt Injection | 用户输入或外部文档中嵌入恶意指令，诱导 LLM 执行非预期操作          | 高       |
| 路径遍历         | LLM 生成的代码访问项目目录之外的敏感文件 (如 `~/.ssh/`, `~/.aws/`) | 高       |
| 命令注入         | LLM 生成的 shell 命令中拼接了未经验证的用户输入                    | 高       |
| 数据泄露         | LLM 将敏感信息 (密钥、token) 包含在输出或 API 调用中               | 高       |
| 资源滥用         | LLM 进入无限循环、生成大量文件、消耗过多 CPU/内存                  | 中       |
| 依赖风险         | LLM 引入恶意或有漏洞的第三方包                                     | 中       |
| 权限提升         | 通过工具链组合，突破单个工具的权限边界                             | 高       |

### 二、第一层防线：沙箱隔离

所有代码执行必须在隔离环境中完成，不能直接在宿主机上运行。

#### 2.1 容器级隔离

```python
import docker

class SandboxExecutor:
    """基于 Docker 的沙箱执行器"""

    def __init__(self):
        self.client = docker.from_env()

    def run_code(self, code: str, language: str = "python") -> dict:
        """在隔离容器中执行代码"""
        container = self.client.containers.run(
            image="sandbox-python:3.11",
            command=["python", "-c", code],
            # 关键安全配置
            network_mode="none",           # 禁用网络，防止数据外传
            read_only=True,                # 只读文件系统
            volumes={
                "/workspace": {
                    "bind": "/workspace",
                    "mode": "ro"           # 项目目录只读挂载
                }
            },
            mem_limit="512m",              # 内存限制
            cpu_period=100000,
            cpu_quota=50000,               # CPU 限制 (50%)
            pids_limit=100,                # 进程数限制
            security_opt=["no-new-privileges"],  # 禁止提权
            detach=True
        )

        result = container.wait(timeout=30)  # 超时强制终止
        logs = container.logs().decode("utf-8")
        container.remove(force=True)

        return {
            "exit_code": result["StatusCode"],
            "output": logs
        }
```

#### 2.2 系统调用级隔离 (Seccomp + AppArmor)

对于更高安全要求的场景，可以在容器内进一步限制系统调用：

```json
{
    "defaultAction": "SCMP_ACT_ERRNO",
    "architectures": ["SCMP_ARCH_X86_64"],
    "syscalls": [
        {
            "names": [
                "read", "write", "open", "close",
                "stat", "fstat", "mmap", "mprotect",
                "brk", "exit_group"
            ],
            "action": "SCMP_ACT_ALLOW"
        }
    ]
}
```

只允许最基本的系统调用，禁止 `socket`, `connect`, `execve` 等危险调用。

### 三、第二层防线：权限最小化

每个 Tool 的权限范围必须严格限定，遵循最小权限原则 (Principle of Least Privilege)。

#### 3.1 Tool 权限分级

```python
from enum import Enum
from dataclasses import dataclass

class PermissionLevel(Enum):
    READ = "read"           # 只读操作：读文件、搜索代码
    WRITE = "write"         # 写操作：编辑文件、创建文件
    EXECUTE = "execute"     # 执行操作：运行命令、调用 API
    DESTRUCTIVE = "destructive"  # 破坏性操作：删除文件、force push

@dataclass
class ToolPermission:
    name: str
    level: PermissionLevel
    requires_confirmation: bool
    allowed_paths: list[str] | None = None
    allowed_commands: list[str] | None = None

# 工具权限注册表
TOOL_PERMISSIONS = {
    "read_file": ToolPermission(
        name="read_file",
        level=PermissionLevel.READ,
        requires_confirmation=False,
        allowed_paths=["/workspace/**"]    # 只能读项目目录
    ),
    "edit_file": ToolPermission(
        name="edit_file",
        level=PermissionLevel.WRITE,
        requires_confirmation=False,
        allowed_paths=["/workspace/**"]
    ),
    "run_command": ToolPermission(
        name="run_command",
        level=PermissionLevel.EXECUTE,
        requires_confirmation=True,         # 执行命令需确认
        allowed_commands=["npm", "python", "pytest", "git"]
    ),
    "delete_file": ToolPermission(
        name="delete_file",
        level=PermissionLevel.DESTRUCTIVE,
        requires_confirmation=True,         # 删除必须确认
        allowed_paths=["/workspace/**"]
    ),
    "git_push": ToolPermission(
        name="git_push",
        level=PermissionLevel.DESTRUCTIVE,
        requires_confirmation=True          # 推送必须确认
    ),
}
```

#### 3.2 路径校验与命令白名单

```python
import os
import shlex

class SecurityGuard:
    """安全校验器"""

    def __init__(self, workspace_root: str):
        self.workspace_root = os.path.realpath(workspace_root)

    def validate_path(self, requested_path: str) -> bool:
        """校验路径是否在允许范围内 (防路径遍历)"""
        real_path = os.path.realpath(requested_path)
        # 关键：用 realpath 解析符号链接后再比较前缀
        return real_path.startswith(self.workspace_root + os.sep) or \
               real_path == self.workspace_root

    def validate_command(self, command: str, allowed: list[str]) -> bool:
        """校验命令是否在白名单中"""
        try:
            parts = shlex.split(command)
        except ValueError:
            return False
        if not parts:
            return False
        # 检查基础命令是否在白名单
        base_cmd = os.path.basename(parts[0])
        return base_cmd in allowed

    def sanitize_output(self, output: str) -> str:
        """脱敏输出中的敏感信息"""
        import re
        # 移除可能的 API key、token 等
        patterns = [
            (r'(api[_-]?key|token|secret|password)\s*[=:]\s*\S+',
             r'\1=***REDACTED***'),
            (r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----.*?-----END',
             '***REDACTED PRIVATE KEY***'),
            (r'ghp_[a-zA-Z0-9]+', '***REDACTED_GITHUB_TOKEN***'),
            (r'sk-[a-zA-Z0-9]{20,}', '***REDACTED_API_KEY***'),
        ]
        sanitized = output
        for pattern, replacement in patterns:
            sanitized = re.sub(pattern, replacement, sanitized,
                             flags=re.IGNORECASE | re.DOTALL)
        return sanitized
```

### 四、第三层防线：输入输出审计

对 LLM 的输入和输出进行静态分析和动态检测。

#### 4.1 输入审计 (防 Prompt Injection)

```python
class InputAuditor:
    """输入审计器：检测 prompt injection 等攻击"""

    # 已知的 prompt injection 模式
    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"you\s+are\s+now\s+(a|an)\s+",
        r"system\s*:\s*you\s+are",
        r"<\|im_start\|>\s*system",
        r"forget\s+(everything|all)\s+(you|above)",
        r"new\s+instructions\s*:",
        r"disregard\s+(all|the|any)\s+",
    ]

    def check_injection(self, user_input: str) -> tuple[bool, str]:
        """检测输入是否包含 prompt injection 攻击"""
        import re
        for pattern in self.INJECTION_PATTERNS:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                return True, f"Detected injection pattern: {match.group()}"
        return False, ""

    def check_sensitive_access(self, code: str) -> list[str]:
        """检测代码中对敏感路径的访问"""
        import re
        warnings = []
        sensitive_paths = [
            r"~/\.ssh",
            r"~/\.aws",
            r"~/\.env",
            r"/etc/passwd",
            r"/etc/shadow",
            r"\.git/config",
        ]
        for path in sensitive_paths:
            if re.search(path, code):
                warnings.append(f"Code accesses sensitive path: {path}")
        return warnings
```

#### 4.2 输出审计 (防数据泄露)

```python
class OutputAuditor:
    """输出审计器：检测 LLM 输出中的风险"""

    def audit_tool_calls(self, tool_calls: list[dict]) -> list[dict]:
        """审计 LLM 请求的工具调用"""
        flagged = []
        for call in tool_calls:
            tool_name = call.get("name", "")
            args = call.get("arguments", {})

            # 检测危险的 shell 命令
            if tool_name == "run_command":
                cmd = args.get("command", "")
                dangerous_patterns = [
                    r"rm\s+-rf\s+/",        # 根目录删除
                    r"curl\s+.*\|\s*sh",    # 远程脚本执行
                    r"chmod\s+777",         # 过度开放权限
                    r">\s*/dev/sd",         # 写入磁盘设备
                    r"dd\s+if=",            # 磁盘操作
                    r"wget.*\|\s*bash",     # 远程脚本执行
                    r"eval\s*\(",           # 动态代码执行
                    r"exec\s*\(",           # 动态代码执行
                    r"subprocess\.call.*shell\s*=\s*True",  # shell 注入
                ]
                import re
                for pattern in dangerous_patterns:
                    if re.search(pattern, cmd):
                        flagged.append({
                            "tool": tool_name,
                            "reason": f"Dangerous command pattern: {pattern}",
                            "command": cmd
                        })

            # 检测对敏感路径的写操作
            if tool_name in ("edit_file", "write_file", "delete_file"):
                path = args.get("file_path", "")
                guard = SecurityGuard("/workspace")
                if not guard.validate_path(path):
                    flagged.append({
                        "tool": tool_name,
                        "reason": f"Path outside workspace: {path}",
                    })

        return flagged
```

### 五、人在回路 (Human-in-the-Loop)

技术手段再完善，也无法覆盖所有 edge case。最终的安全兜底是**人**。

```python
class ConfirmationManager:
    """用户确认管理器"""

    # 需要用户确认的操作类型
    CONFIRM_REQUIRED = {
        "destructive": [
            "delete_file", "remove_directory", "git_reset_hard",
            "git_push_force", "drop_table", "truncate_table"
        ],
        "external": [
            "send_email", "create_pr", "merge_pr", "deploy",
            "publish_package"
        ],
        "sensitive": [
            "read_env_file", "access_credentials", "modify_config"
        ]
    }

    async def request_confirmation(
        self, action: str, details: dict
    ) -> bool:
        """请求用户确认"""
        print(f"\n⚠️  安全确认请求")
        print(f"操作: {action}")
        print(f"详情: {details}")
        print(f"风险级别: {self._get_risk_level(action)}")

        response = input("是否允许此操作？(yes/no): ").strip().lower()
        return response in ("yes", "y")

    def _get_risk_level(self, action: str) -> str:
        for level, actions in self.CONFIRM_REQUIRED.items():
            if action in actions:
                return level
        return "normal"
```

### 六、纵深防御架构总览

```text
用户输入
    ↓
[输入审计层] → 检测 Prompt Injection、敏感关键词
    ↓
[权限校验层] → Tool 白名单、路径校验、命令校验
    ↓
[沙箱执行层] → Docker/VM 隔离、资源限制、网络隔离
    ↓
[输出审计层] → 脱敏处理、危险操作拦截
    ↓
[确认层]    → 高危操作二次确认
    ↓
结果返回用户
```

关键原则：

1. **纵深防御**：不依赖单一安全层，任何一层被突破，下一层仍然有效
2. **默认拒绝**：未明确允许的操作一律拒绝，而不是"未明确禁止的都允许"
3. **最小权限**：每个组件只拥有完成其任务所需的最少权限
4. **可审计**：所有操作都有日志，便于事后追溯和分析
5. **安全与体验平衡**：过度确认会导致用户疲劳 (confirmation fatigue)，反而降低安全性

### 七、面试可直接复述的总结

可以这样回答：Agent 编程工具的安全设计，我会从威胁模型出发，采用纵深防御策略。第一层是沙箱隔离，所有代码执行在 Docker 容器中完成，禁用网络、限制资源、只读挂载项目目录，从环境层面阻断攻击面。第二层是权限最小化，每个 Tool 注册明确的权限等级和允许范围，路径访问用 realpath 校验防遍历，命令执行用白名单过滤，输出做脱敏处理防数据泄露。第三层是输入输出审计，用正则和语义分析检测 prompt injection、shell 注入等攻击模式。最后引入人在回路机制，对删除文件、推送代码、修改配置等高危操作要求用户显式确认。设计上要避免过度确认导致的确认疲劳——读文件、搜索代码等低风险操作可以静默执行，只有破坏性操作才弹确认。安全和体验是需要平衡的，核心原则是"默认拒绝、纵深防御、可审计追溯"。

### 知识扩展

- OWASP Top 10 for LLM Applications：OWASP 发布了针对 LLM 应用的十大安全风险清单，包括 Prompt Injection、Insecure Output Handling、Excessive Agency 等，是 Agent 安全设计的重要参考。
- Sandboxing & Container Security：沙箱技术 (Docker, gVisor, Firecracker) 是云原生安全的基础设施，Agent 安全是其在 AI 领域的直接应用。
- Prompt Injection 攻防：这是一场持续的攻防博弈，从直接注入到间接注入 (通过外部文档、网页)，防御手段也在不断演进 (如 Sandwich Defense、Input/Output Filtering)。
- Principle of Least Privilege：最小权限原则是信息安全的基石，不仅适用于 Agent 工具设计，也是操作系统、数据库、微服务架构的基本安全准则。
- Constitutional AI (CAI)：Anthropic 提出的宪法 AI 方法，通过让模型自我批评和修正来增强安全性，可以作为 Agent 安全的补充手段——让 LLM 自身具备安全意识。
- Guardrails & Safety Filters：如 NeMo Guardrails、Llama Guard 等工具，在 LLM 输入输出层面增加安全过滤层，与 Agent 的沙箱防御形成互补。
- Formal Verification：对于高安全要求的场景，可以考虑对 LLM 生成的代码做形式化验证，确保满足安全不变量，虽然目前成本较高但代表了未来方向。
- Code Review Automation：Agent 生成的代码在执行前可以经过自动化安全扫描 (如 Semgrep, Bandit)，将安全左移 (Shift Left Security) 的理念应用到 AI 编程工具中。

## 2.15 Agent 的"规划-执行-反思"闭环如何实现？

Agent 的"规划-执行-反思" (Plan-Execute-Reflect) 闭环是让 Agent 从"一次性指令执行器"升级为"自主迭代优化系统"的核心机制。它的本质是：**不要求一次做对，而是允许做错、检测错误、修正后重来**——模拟人类解决复杂问题时"想一想、做一做、回头看"的思维过程。

### 一、为什么需要这个闭环？

纯 ReAct 模式 (Thought -> Action -> Observation 循环) 存在两个根本性缺陷：

1. **缺乏全局视野**：每一步只看当前上下文决定下一步，没有对整体目标的规划，容易在复杂任务上走弯路或陷入局部最优。
2. **缺乏质量保障**：执行完就输出结果，没有"回头看"的过程，错误会直接暴露给用户。

规划-执行-反思闭环的核心价值是：

- 规划 (Plan)：解决"做什么"和"按什么顺序做"的问题，给 Agent 一个全局路线图。
- 执行 (Execute)：解决"怎么做"的问题，按计划逐步调用工具完成子任务。
- 反思 (Reflect)：解决"做得对不对"的问题，对执行结果进行质量评估，发现问题后触发修正。

### 二、闭环架构总览

```text
用户请求
    ↓
┌──────────────────────────────────────────────┐
│            [规划阶段 - Planner]               │
│  分析任务 → 拆解子目标 → 生成执行计划         │
│  输出：Plan = [Step1, Step2, ..., StepN]      │
└──────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────┐
│           [执行阶段 - Executor]               │
│  按计划逐步执行：                             │
│  for step in Plan:                            │
│      result = execute(step)                   │
│      store(step, result)                      │
└──────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────┐
│           [反思阶段 - Reflector]              │
│  评估执行结果：                               │
│  - 结果是否满足任务目标？                      │
│  - 是否有步骤失败或输出异常？                  │
│  - 是否需要调整计划？                         │
│  输出：PASS → 返回最终结果                    │
│        FAIL → 修正计划 → 回到执行阶段         │
└──────────────────────────────────────────────┘
    ↓ (如果 PASS)
返回最终结果给用户
```

关键点：这个闭环不是只跑一轮，而是可以多轮迭代。每一轮反思可能触发计划修正，修正后重新执行，直到满足终止条件。

### 三、三个阶段的详细实现

#### 1. 规划阶段 (Planning)

规划阶段的核心任务是将用户的高层请求分解为可执行的子步骤序列。

**常见规划策略：**

| 策略                  | 原理                       | 适用场景                     |
| --------------------- | -------------------------- | ---------------------------- |
| One-shot Planning     | 一次性生成完整计划         | 任务结构清晰、步骤可预见     |
| Iterative Planning    | 边执行边细化后续计划       | 任务不确定性高、需要动态调整 |
| Hierarchical Planning | 先生成高层计划，再逐层细化 | 复杂多层级任务               |
| Re-planning           | 执行失败后重新生成计划     | 错误恢复场景                 |

**规划的 Prompt 设计要点：**

```text
你是一个任务规划器。请将以下用户请求分解为有序的子步骤列表。

要求：
1. 每个步骤应该是独立可执行的原子操作
2. 步骤之间需要明确依赖关系
3. 为每个步骤标注预期输出格式
4. 标注哪些步骤可以并行执行

用户请求：{user_query}
可用工具：{tool_descriptions}

输出格式 (JSON)：
{
  "goal": "任务目标描述",
  "steps": [
    {"id": 1, "action": "具体动作", "tool": "工具名", "depends_on": [], "expected_output": "预期输出"}
  ]
}
```

**规划的关键难点——粒度控制：**

- 太粗：步骤过于笼统，Executor 不知道具体怎么做。
- 太细：步骤过多，累积误差大，且 LLM 长列表容易丢失后面的内容。
- 经验法则：一个计划通常 3-8 个步骤为宜，每个步骤对应一次或少数几次工具调用。

#### 2. 执行阶段 (Execution)

执行阶段按计划逐步调用工具完成子任务，核心挑战是**状态管理**和**错误处理**。

**执行引擎的关键设计：**

```python
class PlanExecutor:
    def __init__(self, tools, llm):
        self.tools = tools
        self.llm = llm
        self.results = {}      # 存储每步结果
        self.context = []      # 执行上下文

    def execute_plan(self, plan):
        for step in plan.steps:
            # 1. 构建当前步骤的输入（依赖前序步骤的结果）
            step_input = self._resolve_dependencies(step)

            # 2. 执行当前步骤
            try:
                result = self._execute_step(step, step_input)
                self.results[step.id] = result
                self.context.append({
                    "step_id": step.id,
                    "action": step.action,
                    "result": result,
                    "status": "success"
                })
            except Exception as e:
                self.context.append({
                    "step_id": step.id,
                    "action": step.action,
                    "error": str(e),
                    "status": "failed"
                })
                # 触发错误处理（回滚或重新规划）
                return self._handle_failure(step, e)

        return self.results

    def _execute_step(self, step, step_input):
        """根据步骤定义调用对应工具"""
        tool = self.tools[step.tool]
        return tool.run(**step_input)

    def _resolve_dependencies(self, step):
        """从已执行步骤的结果中提取当前步骤的输入"""
        inputs = {}
        for dep_id in step.depends_on:
            inputs[f"step_{dep_id}_result"] = self.results[dep_id]
        return inputs

    def _handle_failure(self, failed_step, error):
        """失败处理：记录失败信息，供反思阶段决策"""
        return {
            "status": "failed",
            "failed_step": failed_step.id,
            "error": str(error),
            "partial_results": self.results,
            "context": self.context
        }
```

#### 3. 反思阶段 (Reflection)

反思阶段是整个闭环的大脑，它需要回答三个核心问题：

1. **结果正确吗？** (Correctness)——输出是否满足用户需求。
2. **过程合理吗？** (Process Quality)——执行路径是否高效、有没有冗余步骤。
3. **需要修正吗？** (Action Decision)——决定是终止、重试还是重新规划。

**反思的评估维度：**

```text
反思检查清单 (Reflection Checklist)
├── 任务完成度 (Goal Fulfillment)
│   └── 所有子目标是否都已达成？
├── 结果一致性 (Consistency)
│   └── 各步骤结果之间是否矛盾？
├── 事实准确性 (Factual Grounding)
│   └── 生成内容是否有工具输出支撑？是否产生幻觉？
├── 约束满足度 (Constraint Satisfaction)
│   └── 是否违反预算、时间、权限等约束？
└── 效率评估 (Efficiency)
    └── 是否存在不必要的步骤或可优化的路径？
```

**反思的 Prompt 设计：**

```text
你是一个任务执行审查员。请根据以下信息评估执行结果。

任务目标：{goal}
执行计划：{plan}
执行结果：{results}
执行日志：{context}

请从以下维度评估：
1. 任务是否完成？ (yes/no/partial)
2. 如果未完成或部分完成，失败原因是什么？
3. 是否需要重新规划？如果需要，请给出修正后的计划。

输出格式 (JSON)：
{
  "task_completed": "yes|no|partial",
  "score": 0.0-1.0,
  "issues": ["问题1", "问题2"],
  "recommendation": "terminate|retry|replan",
  "revised_plan": null 或修正后的计划
}
```

### 四、闭环在 LangGraph 中的完整实现

LangGraph 是实现 Plan-Execute-Reflect 闭环最常用的框架，因为它天然支持状态图、条件边和循环。

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

class AgentState(TypedDict):
    user_query: str
    plan: list[dict]                # 执行计划
    current_step: int               # 当前执行到第几步
    results: Annotated[list, operator.add]  # 各步结果
    reflection: dict                # 反思结果
    iteration: int                  # 当前迭代轮次
    max_iterations: int             # 最大迭代轮次
    final_answer: str               # 最终输出

# ---- 节点函数 ----

def planner(state: AgentState) -> dict:
    """规划节点：根据用户请求生成执行计划"""
    plan = llm_plan(state["user_query"], available_tools)
    return {"plan": plan, "current_step": 0, "iteration": state.get("iteration", 0) + 1}

def executor(state: AgentState) -> dict:
    """执行节点：执行计划中的当前步骤"""
    step = state["plan"][state["current_step"]]
    result = execute_tool(step["tool"], step["input"], state["results"])
    return {
        "results": [result],
        "current_step": state["current_step"] + 1
    }

def reflector(state: AgentState) -> dict:
    """反思节点：评估执行结果，决定下一步动作"""
    reflection = llm_reflect(
        goal=state["user_query"],
        plan=state["plan"],
        results=state["results"],
        context=build_context(state)
    )
    return {"reflection": reflection}

# ---- 条件路由函数 ----

def should_continue_execution(state: AgentState) -> str:
    """判断是否继续执行当前计划的下一步"""
    if state["current_step"] < len(state["plan"]):
        return "executor"      # 还有步骤未执行
    return "reflector"         # 所有步骤执行完毕，进入反思

def should_terminate(state: AgentState) -> str:
    """反思后决定：终止、重试还是重新规划"""
    reflection = state["reflection"]

    if reflection["task_completed"] == "yes":
        return "terminate"     # 任务完成，输出结果

    if state["iteration"] >= state["max_iterations"]:
        return "terminate"     # 达到最大迭代次数，强制终止

    if reflection["recommendation"] == "replan":
        return "planner"       # 需要重新规划
    else:
        return "executor"      # 重试当前步骤

# ---- 构建状态图 ----

graph = StateGraph(AgentState)

# 添加节点
graph.add_node("planner", planner)
graph.add_node("executor", executor)
graph.add_node("reflector", reflector)

# 设置入口
graph.set_entry_point("planner")

# 添加边
graph.add_conditional_edges("planner", should_continue_execution, {
    "executor": "executor",
    "reflector": "reflector"
})
graph.add_conditional_edges("executor", should_continue_execution, {
    "executor": "executor",    # 继续执行下一步
    "reflector": "reflector"   # 进入反思
})
graph.add_conditional_edges("reflector", should_terminate, {
    "terminate": END,          # 任务结束
    "planner": "planner",      # 重新规划
    "executor": "executor"     # 重试
})

app = graph.compile()
```

执行流程图：

```text
              ┌──────────────────────────────────────┐
              │                                      │
              ↓                                      │
         ┌─────────┐    steps remain    ┌──────────┐ │
    ───→ │ Planner │ ─────────────────→ │ Executor │ │
         └─────────┘                    └──────────┘ │
              ↑                          ↓     ↑     │
              │                    done ↓     │     │
              │                   ┌──────────┐│     │
              │                   │Reflector ││     │
              │                   └──────────┘│     │
              │                    ↓          │     │
              │              replan           │     │
              └───────────────────────────────┘     │
                    ↓                               │
                  retry ─────────────────────────────┘
                    ↓
                  END (task completed or max iterations)
```

### 五、反思的三种模式

根据反思的深度和时机，可以分为三种模式：

#### 模式一：Step-level Reflection (步骤级反思)

每执行完一步立刻反思，发现问题立即修正。

```text
Step1 → Reflect → (pass) → Step2 → Reflect → (pass) → Step3 → Reflect → Done
                              ↓
                           (fail) → Fix Step2 → Re-reflect → Step3 ...
```

优点：错误发现早，修复成本低。缺点：反思开销大，每步都多一次 LLM 调用。

#### 模式二：Plan-level Reflection (计划级反思)

执行完整个计划后统一反思，适合步骤间有强依赖的场景。

```text
Step1 → Step2 → Step3 → Reflect → (pass) → Done
                                   ↓
                                (fail) → Re-plan → Step1' → Step2' → ...
```

优点：反思更全面，能看到全局问题。缺点：错误发现晚，失败步骤可能已经污染了后续结果。

#### 模式三：Hybrid Reflection (混合反思)

关键步骤即时反思 + 最终整体反思，兼顾局部和全局。

```text
Step1 → Step2 → [Checkpoint] → Reflect → Step3 → Step4 → [Checkpoint] → Reflect → Final Reflect
```

这是生产环境最常用的模式，在成本和质量之间取得平衡。

### 六、终止条件设计

闭环必须有明确的终止条件，否则可能无限循环。常见的终止条件包括：

```text
终止条件 (任一触发即终止)
├── 目标达成：反思阶段判定任务完成
├── 最大迭代次数：防止无限循环 (通常 3-5 轮)
├── 最大步数限制：整个执行过程的总步骤数上限
├── 成本预算：LLM 调用次数或 Token 消耗达到上限
├── 质量收敛：连续两轮反思的评分无显著提升
└── 人工干预：用户主动终止或系统检测到异常模式
```

质量收敛条件的判断逻辑：

$$
\Delta Quality = Score_{t} - Score_{t-1}
$$

$$
terminate \quad if \quad \Delta Quality < \epsilon \quad or \quad Score_t \geq Threshold
$$

当质量提升低于某个阈值 $\epsilon$ (如 0.05) 时，继续迭代的边际收益很低，应终止并返回当前最优结果。

### 七、工程实践中的关键问题

#### 1. 如何避免"反思幻觉"？

反思阶段本身也是 LLM 在做，它可能会误判执行结果为"正确" (实际上有错误)，或误判为"错误" (实际上没问题)。

解决方案：

- 用**确定性校验器**辅助反思：Schema 校验、约束检查、事实核验等不依赖 LLM 判断的硬规则。
- 让反思模型和执行模型**分离**：用不同模型或不同 Prompt 分别负责执行和反思，降低"自我欺骗"概率。
- 引入**外部评估信号**：如用户反馈、工具返回的状态码、API 的错误信息等客观数据。

#### 2. 如何控制闭环的推理成本？

每多一轮迭代，就多一轮完整的 Plan + Execute + Reflect 的 LLM 调用开销。在生产环境中必须严格控制。

成本控制策略：

- **渐进式反思**：前几步只做轻量级检查 (规则校验)，最后才做完整的 LLM 反思。
- **预算门控**：设置每轮迭代的 Token 上限，超出后强制降级为简单重试。
- **缓存中间结果**：已完成且通过验证的步骤结果不要重复计算。
- **快速失败 (Fail Fast)**：在执行阶段遇到硬性错误 (如工具不存在、权限不足) 直接终止，不必走完整反思流程。

#### 3. 多 Agent 场景下的闭环

在 Multi-Agent 架构中，规划-执行-反思闭环可以在两个层级发生：

- **全局闭环**：Orchestrator Agent 负责全局规划和最终反思，各 Worker Agent 只负责执行。
- **局部闭环**：每个 Worker Agent 内部有自己的小闭环，处理局部失败。

```text
Orchestrator: Plan → dispatch to Workers → Collect results → Reflect
    Worker A: Sub-plan → Execute → Local reflect → Report
    Worker B: Sub-plan → Execute → Local reflect → Report
```

### 八、面试可直接复述的总结

可以这样回答：Agent 的"规划-执行-反思"闭环本质上是一个自主迭代优化系统，由三个核心阶段组成。规划阶段将用户请求分解为有序的子步骤计划，解决"做什么"的问题；执行阶段按计划逐步调用工具完成子任务，解决"怎么做"的问题；反思阶段对执行结果进行多维度评估 (完成度、一致性、准确性)，解决"做得对不对"的问题。如果反思发现问题，系统会根据问题类型选择重试、局部重规划或全局重规划，形成闭环迭代。在工程实现上，我通常使用 LangGraph 的状态图来建模这个闭环，用条件边控制"继续执行-进入反思-重新规划"的流转逻辑。反思模式上，生产环境通常采用混合反思策略——关键步骤即时检查加最终整体评估，兼顾错误发现的及时性和全局视野。终止条件方面，需要设置最大迭代次数、成本预算和质量收敛阈值，防止无限循环。此外还需要注意反思幻觉问题，用确定性校验器辅助 LLM 反思，并通过缓存和预算门控控制推理成本。

### 知识扩展

- **ReAct 范式**：Plan-Execute-Reflect 可以看作 ReAct 的增强版——ReAct 是"边想边做"，而 PER 增加了全局规划和质量反思两个维度，适合更复杂的任务。详见 2.5 节。
- **Self-Correction 机制**：反思阶段的"发现问题-归因-修复"流程与 Agent 自我纠正机制高度重合，本质上反思是 Self-Correction 的触发器。详见 2.8 节。
- **LangGraph 状态机**：闭环的条件边循环、状态快照和回滚机制都依赖 LangGraph 的图结构能力，是实现闭环的首选框架。
- **Memory System**：反思产生的经验 (哪些策略有效、哪些工具容易失败) 应该沉淀到长期记忆中，避免重复犯错。详见第 3 节。
- **Reward Model / Evals**：反思阶段的质量评分可以借鉴 RLHF 中的 Reward Model 思路，训练专门的评估模型替代 LLM 自评，提高反思的客观性。
- **Tree of Thoughts (ToT)**：规划阶段生成多个候选计划、反思阶段选择最优路径的模式，本质上是 ToT 思想在 Agent 系统中的工程化应用。
