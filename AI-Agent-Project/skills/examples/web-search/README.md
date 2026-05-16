# Web Search Skill

中级 Skill 示例，演示如何开发一个集成外部 HTTP API 的搜索技能。

## 功能

- 多搜索引擎支持（Google / Bing / DuckDuckGo）
- 请求重试与超时控制
- 结果缓存（TTL）
- 并发搜索与结果聚合
- 速率限制

## 学习要点

| 知识点 | 说明 |
|--------|------|
| HTTP 工具集成 | 调用外部 REST API |
| 重试机制 | 指数退避重试策略 |
| 缓存层 | 内存缓存 + TTL 过期 |
| 并发控制 | goroutine + WaitGroup |
| 配置外部化 | 超时/重试次数等通过配置管理 |

## 项目结构

```
web-search/
├── README.md
├── skill.yaml          # Skill 清单
├── handler.go          # 搜索处理器
├── search_client.go    # HTTP 客户端封装
├── cache.go            # 缓存实现
├── handler_test.go     # 单元测试
└── main.go             # 运行入口
```
