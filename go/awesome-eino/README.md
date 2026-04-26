# Eino 框架

Eino['aino] 是一个基于 Go 语言实现的 AI 应用开发框架（Agent Development Kit），旨在帮助开发者快速构建可扩展、可维护的 AI 应用。框架名称发音类似 "i know"，寓意让开发者能够轻松构建智能应用。

Eino 借鉴了 LangChain、LlamaIndex、Google ADK 等开源框架的优秀设计，同时融入了前沿研究成果和实践经验，提供了更符合 Go 编程惯例的 AI 应用开发框架。

## 核心仓库

- **[eino](https://github.com/cloudwego/eino)**：核心库，定义接口、编排抽象和 ADK
- **[eino-ext](https://github.com/cloudwego/eino-ext)**：扩展库，提供各类 Component 的具体实现（OpenAI、Ark、Milvus 等）
- **[eino-examples](https://github.com/cloudwego/eino-examples)**：示例代码库

## 核心特性

Eino 定义了一组 Component 接口，每个接口描述一类可替换的能力：

- **ChatModel**：大语言模型接口
- **Tool**：工具接口
- **Retriever**：检索器接口
- **Loader**：加载器接口

### 编排能力

Eino 提供了三套编排 API：

1. **Agent**：简化的 Agent 抽象，开箱即用
   - `ChatModelAgent`：单轮或多轮对话 Agent
   - `DeepAgent`：复杂任务分解 Agent，可协调多个子 Agent

2. **Graph**：有向无环图编排，支持条件分支、循环等复杂流程

3. **Workflow**：工作流编排，支持灵活的步骤协调

## 快速开始

### 前置条件

- Go 1.21+
- 一个可调用的 ChatModel

### 环境配置

```bash
# OpenAI 配置
export OPENAI_API_KEY="your-api-key"
export OPENAI_MODEL="gpt-4o-mini"

# 或使用 Ark
export MODEL_TYPE="ark"
export ARK_API_KEY="your-api-key"
export ARK_MODEL="your-model"
```

### 基本使用

#### 1. 创建 ChatModel

```go
import (
    "context"
    "log"

    "github.com/cloudwego/eino-ext/chatopenai"
)

model, err := chatopenai.NewChatModel(context.Background(), &chatopenai.ChatModelConfig{
    Model:  "gpt-4o-mini",
    APIKey: "your-api-key",
})
if err != nil {
    log.Fatal(err)
}
```

#### 2. 调用生成

```go
import (
    "github.com/cloudwego/eino/schema"
)

result, err := model.Generate(context.Background(), []*schema.Message{
    schema.SystemMessage("你是一个有帮助的助手。"),
    schema.UserMessage("什么是 AI？"),
})
```

#### 3. 流式输出

```go
stream, err := model.Stream(context.Background(), []*schema.Message{
    schema.SystemMessage("你是一个有帮助的助手。"),
    schema.UserMessage("什么是 AI？"),
})

reader, _ := stream.Reader()
for {
    msg, err := reader.Read(context.Background())
    if err != nil {
        break
    }
    print(msg.Content)
}
```

### 使用 Agent

```go
import (
    "context"
    "log"

    "github.com/cloudwego/eino/adk"
)

agent, err := adk.NewChatModelAgent(context.Background(), &adk.ChatModelAgentConfig{
    Model: model,
})
if err != nil {
    log.Fatal(err)
}

result, err := agent.Run(context.Background(), "请介绍一下 Eino 框架")
```

### 添加 Tools

```go
agent, err := adk.NewChatModelAgent(context.Background(), &adk.ChatModelAgentConfig{
    Model: model,
    ToolsConfig: adk.ToolsConfig{
        ToolsNodeConfig: compose.ToolsNodeConfig{
            Tools: []tool.BaseTool{weatherTool, calculatorTool},
        },
    },
})
```

### 使用 DeepAgent

DeepAgent 用于复杂任务，可将问题分解为步骤并委托给子 Agent：

```go
import "github.com/cloudwego/eino/deep"

deepAgent, err := deep.New(context.Background(), &deep.Config{
    ChatModel: model,
    SubAgents: []adk.Agent{researchAgent, codeAgent},
})
```

### 使用 Graph 编排

```go
import (
    "github.com/cloudwego/eino/compose"
)

graph := compose.NewGraph[*schema.Message](context.Background())
graph.AddNode("loader", compose.NewLoaderNode(loader))
graph.AddNode("retriever", compose.NewRetrieverNode(retriever))
graph.AddNode("chat", compose.NewChatModelNode(model))

graph.AddEdge("loader", "retriever")
graph.AddEdge("retriever", "chat")
```

## 项目结构

```
awesome-eino/
├── README.md
```

## 文档资源

- [Eino 官方文档](https://www.cloudwego.io/zh/docs/eino/overview/)
- [Eino Quick Start](https://www.cloudwego.io/zh/docs/eino/quick_start/)
- [Eino GitHub](https://github.com/cloudwego/eino)
- [eino-examples](https://github.com/cloudwego/eino-examples)
- [API 参考](https://pkg.go.dev/github.com/cloudwego/eino)

## 许可证

MIT License