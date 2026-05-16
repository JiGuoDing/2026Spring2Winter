# AI Agent Skill 术语表

## 核心概念

| 术语 | 英文 | 定义 |
|------|------|------|
| 技能 | Skill | AI Agent 可执行的最小功能单元，拥有独立的输入/输出定义和处理逻辑 |
| 技能清单 | Skill Manifest | 描述技能元数据、输入/输出规范和配置的 YAML 文件 (skill.yaml) |
| 技能注册表 | Skill Registry | 集中管理所有已注册技能的目录服务，提供发现和路由功能 |
| 技能执行器 | Skill Executor | 负责加载、实例化和执行技能的运行时组件 |
| 技能生命周期 | Skill Lifecycle | 技能从创建到退役的完整过程：CREATE → BUILD → TEST → REGISTER → DEPLOY → ACTIVE → UPDATE → DEPRECATE → RETIRE |
| 技能编排 | Skill Orchestration | 多个技能按特定流程协调执行的过程 |
| 意图路由 | Intent Routing | 根据用户意图将请求分发到对应技能的机制 |
| 上下文管理 | Context Management | 维护会话状态和历史消息的能力 |

## 架构组件

| 术语 | 英文 | 定义 |
|------|------|------|
| 处理器 | Handler | 实现具体业务逻辑的代码单元，对应 Skill Manifest 中定义的输入/输出 |
| 插件 | Plugin | 可嵌入技能的扩展模块，提供可复用的功能（如搜索、缓存、认证） |
| 管道 | Pipeline | 数据处理的流水线模式，由多个可插拔步骤 (Step) 组成 |
| 中间件 | Middleware | 在请求处理前后插入的逻辑层（如日志、认证、限流） |
| 工具 | Tool | 技能可调用的外部资源（HTTP API、数据库、缓存等） |

## 数据与通信

| 术语 | 英文 | 定义 |
|------|------|------|
| 输入模式 | Input Schema | 技能输入参数的 JSON Schema 定义 |
| 输出模式 | Output Schema | 技能输出结果的 JSON Schema 定义 |
| 结构化错误 | SkillError | 包含错误码 (Code)、消息 (Message) 和详情 (Detail) 的标准化错误格式 |
| 流式响应 | Streaming Response | 分块返回结果的方式，适合长时间处理的场景 |
| 事件驱动 | Event-Driven | 通过事件触发技能执行的异步模式 |

## 部署与运维

| 术语 | 英文 | 定义 |
|------|------|------|
| 技能池 | Skill Pool | 同类技能的部署集合，支持自动伸缩 |
| 健康检查 | Health Check | 定期检测技能可用性的机制 |
| 语义版本 | Semantic Versioning | MAJOR.MINOR.PATCH 版本策略，MAJOR 表示不兼容变更 |
| 废弃期 | Deprecation Period | 技能标记为废弃后仍可使用的宽限期 |
| 速率限制 | Rate Limiting | 限制单位时间内请求次数的策略 |
| 熔断器 | Circuit Breaker | 当错误率超过阈值时自动断开，防止级联故障 |

## 测试与质量

| 术语 | 英文 | 定义 |
|------|------|------|
| 表格驱动测试 | Table-Driven Test | 使用测试用例表组织单元测试的 Go 最佳实践 |
| 契约测试 | Contract Test | 验证技能输入/输出是否符合 Schema 定义的测试 |
| 集成测试 | Integration Test | 验证多个组件协同工作的测试 |
| 基准测试 | Benchmark Test | 测量代码执行性能的测试（Go 的 testing.B） |
| Mock 服务器 | Mock Server | 模拟外部 API 行为的测试辅助工具 |
