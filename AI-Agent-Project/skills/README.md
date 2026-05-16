# AI Agent 技能 (Skills) 开发教程

## 项目简介

本项目是一套系统化的 AI Agent 技能开发教程，旨在帮助开发者理解技能架构、掌握技能开发生命周期、学习最佳实践，并能够独立构建可复用的 Agent 技能。

## 适用人群

- 希望为 AI Agent 构建可复用技能的开发者
- 对 Agent 工具调用、插件体系感兴趣的工程师
- 需要标准化技能开发流程的团队

## 项目结构

```
skills/
├── README.md                          # 项目总览
├── docs/                              # 教程文档
│   ├── 01-getting-started.md          # 快速入门
│   ├── 02-skill-architecture.md       # 技能架构设计
│   ├── 03-skill-lifecycle.md          # 技能生命周期
│   ├── 04-plugin-development.md       # 插件开发
│   ├── 05-tool-integration.md         # 工具集成
│   ├── 06-testing-and-debugging.md    # 测试与调试
│   └── 07-best-practices.md           # 最佳实践
├── examples/                          # 代码示例
│   ├── simple-calculator/             # 入门: 简单计算器
│   ├── web-search/                    # 中级: Web 搜索
│   ├── data-analysis/                 # 中级: 数据分析
│   ├── multi-modal-assistant/         # 高级: 多模态助手
│   └── code-generator/                # 高级: 代码生成器
├── templates/                         # 开发模板
│   ├── skill-template.yaml            # Skill 配置模板
│   ├── handler-template.go            # Handler 代码模板
│   └── test-template.go               # 测试代码模板
├── config/                            # 项目配置
│   ├── default-config.yaml            # 默认配置
│   └── skill-registry.yaml            # 技能注册表
└── resources/                         # 参考资源
    ├── glossary.md                    # 术语表
    ├── cheatsheet.md                  # 速查表
    └── references.md                  # 参考资料
```

## 快速开始

1. **阅读入门指南**: 从 [docs/01-getting-started.md](docs/01-getting-started.md) 开始
2. **运行示例**: 进入 `examples/simple-calculator/` 体验第一个技能
3. **使用模板**: 从 `templates/` 复制模板开始构建自己的技能
4. **掌握最佳实践**: 阅读 [docs/07-best-practices.md](docs/07-best-practices.md)

## 核心概念

| 概念 | 说明 |
|------|------|
| Skill (技能) | Agent 可执行的独立功能单元，包含输入定义、处理逻辑和输出格式 |
| Skill Registry (技能注册表) | 管理所有可用技能的中心化注册表 |
| Handler (处理器) | 技能的核心执行逻辑 |
| Manifest (清单) | 技能的元数据描述 (名称、版本、输入/输出 Schema 等) |
| Plugin (插件) | 可动态加载/卸载的技能扩展包 |

## 技能开发核心流程

```
需求分析 → 接口设计 → 实现 Handler → 编写配置 → 注册技能 → 测试验证 → 发布部署
```

## 技术栈

- **编程语言**: Go (示例), 支持 Python 扩展
- **配置格式**: YAML
- **通信协议**: HTTP/gRPC
- **Schema 定义**: JSON Schema

## 许可证

MIT License
