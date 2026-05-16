# 01 - 快速入门

## 学习目标

- 理解 AI Agent 技能 (Skill) 的核心概念
- 搭建技能开发环境
- 创建并运行第一个技能

## 什么是 Skill？

Skill 是 AI Agent 可执行的独立功能单元。每个 Skill 封装了：

| 组成部分 | 说明 | 示例 |
|----------|------|------|
| 输入定义 (Input Schema) | 描述技能需要的参数 | `{"a": "number", "b": "number"}` |
| 处理逻辑 (Handler) | 实现核心功能的代码 | 计算 `a + b` |
| 输出格式 (Output Schema) | 描述返回结果的格式 | `{"result": "number"}` |
| 元数据 (Metadata) | 名称、版本、描述等 | `name: calculator` |

## 环境准备

### 前置条件

- Go 1.21+ 或 Python 3.10+
- 基本的命令行操作能力
- 文本编辑器或 IDE

### 项目初始化

```bash
mkdir my-first-skill && cd my-first-skill
go mod init example.com/my-first-skill
```

## 创建第一个 Skill: Hello World

### Step 1: 编写 Skill 配置 (skill.yaml)

```yaml
name: hello-world
version: 1.0.0
description: "一个简单的问候技能"

input:
  type: object
  properties:
    name:
      type: string
      description: "要问候的用户名"
  required:
    - name

output:
  type: object
  properties:
    greeting:
      type: string
      description: "生成的问候语"
```

### Step 2: 实现 Handler

```go
package main

import (
    "encoding/json"
    "fmt"
)

type HelloWorldInput struct {
    Name string `json:"name"`
}

type HelloWorldOutput struct {
    Greeting string `json:"greeting"`
}

func HelloWorldHandler(input []byte) ([]byte, error) {
    var in HelloWorldInput
    if err := json.Unmarshal(input, &in); err != nil {
        return nil, fmt.Errorf("invalid input: %w", err)
    }

    if in.Name == "" {
        return nil, fmt.Errorf("name is required")
    }

    out := HelloWorldOutput{
        Greeting: fmt.Sprintf("Hello, %s! Welcome to AI Agent Skills.", in.Name),
    }

    return json.Marshal(out)
}
```

### Step 3: 编写测试

```go
package main

import (
    "encoding/json"
    "testing"
)

func TestHelloWorldHandler(t *testing.T) {
    input, _ := json.Marshal(HelloWorldInput{Name: "Developer"})
    output, err := HelloWorldHandler(input)
    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }

    var out HelloWorldOutput
    json.Unmarshal(output, &out)

    if out.Greeting == "" {
        t.Error("greeting should not be empty")
    }
}

func TestHelloWorldHandler_EmptyName(t *testing.T) {
    input, _ := json.Marshal(HelloWorldInput{Name: ""})
    _, err := HelloWorldHandler(input)
    if err == nil {
        t.Fatal("expected error for empty name")
    }
}
```

### Step 4: 运行

```bash
go test -v ./...
```

## Skill 核心设计原则

1. **单一职责**: 每个 Skill 只做一件事，做好
2. **明确契约**: 输入/输出使用 JSON Schema 定义，契约先行
3. **无状态**: Skill 不应依赖外部状态，每次调用应独立
4. **幂等性**: 相同输入产生相同输出 (对于查询类 Skill)
5. **错误透明**: 错误信息应结构化，方便 Agent 理解和重试

## 下一步

- 阅读 [02-skill-architecture.md](02-skill-architecture.md) 了解技能架构设计
- 查看 `examples/simple-calculator/` 了解更复杂的示例
