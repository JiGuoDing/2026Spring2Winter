# Multi-Modal Assistant Skill

高级 Skill 示例，演示如何构建一个多模态助手技能，支持文本、图片和语音的统一处理。

## 功能

- 多模态输入（文本/图片/语音）
- 意图识别与路由
- 技能编排 (Orchestration)
- 上下文管理（对话历史）
- 流式响应输出

## 学习要点

| 知识点 | 说明 |
|--------|------|
| 多模态处理 | 统一处理不同类型的输入 |
| 意图路由 | 根据意图分发到不同子技能 |
| 技能编排 | 多个技能的协调执行 |
| 上下文管理 | 维护对话状态和历史 |
| 流式输出 | Server-Sent Events 风格流式响应 |

## 项目结构

```
multi-modal-assistant/
├── README.md
├── skill.yaml        # Skill 清单
├── handler.go        # 助手主处理器
├── router.go         # 意图路由器
├── context.go        # 上下文管理
├── handler_test.go   # 单元测试
└── main.go           # 运行入口
```
