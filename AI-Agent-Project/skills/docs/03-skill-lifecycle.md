# 03 - 技能生命周期

## 学习目标

- 理解技能从创建到销毁的完整生命周期
- 掌握各阶段的开发要点
- 了解版本管理与兼容性策略

## 生命周期总览

```
    ┌─────────┐
    │  CREATE  │  创建：定义技能描述与接口
    └────┬────┘
         ▼
    ┌─────────┐
    │  BUILD   │  构建：实现核心逻辑
    └────┬────┘
         ▼
    ┌─────────┐
    │  TEST    │  测试：单元测试与集成测试
    └────┬────┘
         ▼
    ┌─────────┐
    │ REGISTER │  注册：加入 Skills Registry
    └────┬────┘
         ▼
    ┌─────────┐
    │ DEPLOY   │  部署：发布到运行环境
    └────┬────┘
         ▼
    ┌─────────┐
    │  ACTIVE  │◄────── 运行中：处理请求 ──┐
    └────┬────┘                            │
         │                                 │
         ├────────  UPDATE ────────────────┘
         ▼
    ┌──────────┐
    │ DEPRECATE │  弃用：标记为非推荐使用
    └────┬─────┘
         ▼
    ┌─────────┐
    │  RETIRE  │  退役：从注册表中移除
    └─────────┘
```

## 阶段详解

### 阶段 1: CREATE (创建)

创建阶段需要回答以下核心问题：

1. 这个技能解决什么问题？
2. 输入是什么？输出是什么？
3. 有哪些边界条件和异常情况？
4. 与其他技能的关系是什么？

**设计文档模板:**

```yaml
skill_design:
  problem_statement: "用户需要搜索网页内容"
  target_users: "所有 Agent 用户"
  input_description: "搜索关键词 (string) 和最大结果数 (int)"
  output_description: "搜索结果列表，每个结果包含标题、URL 和摘要"
  constraints:
    - "单次搜索不超过 50 条结果"
    - "响应时间不超过 3 秒"
  related_skills:
    - "text-summarizer 可对搜索结果进行摘要"
```

### 阶段 2: BUILD (构建)

每个 Skill 必须实现 Skill 接口：

```go
type Skill interface {
    Name() string
    Meta() SkillMeta
    Handle(ctx context.Context, input json.RawMessage) (json.RawMessage, error)
    Validate(input json.RawMessage) error
    HealthCheck(ctx context.Context) error
}

type SkillMeta struct {
    Name        string           `json:"name"`
    Version     string           `json:"version"`
    Description string           `json:"description"`
    Author      string           `json:"author"`
    Tags        []string         `json:"tags"`
    InputSchema json.RawMessage  `json:"input_schema"`
    OutputSchema json.RawMessage `json:"output_schema"`
    Timeout     time.Duration    `json:"timeout"`
    Deprecated  bool             `json:"deprecated,omitempty"`
}
```

### 阶段 3: TEST (测试)

| 测试类型 | 覆盖内容 | 工具 |
|----------|----------|------|
| 单元测试 | Handler 核心逻辑 | go test |
| Schema 测试 | 输入输出格式校验 | JSON Schema validator |
| 集成测试 | 与外部依赖交互 | docker-compose |
| 压力测试 | 高并发场景 | vegeta / wrk |

### 阶段 4: REGISTER (注册)

```go
func RegisterNewSkill() error {
    skill := &WebSearchSkill{
        meta: SkillMeta{
            Name:        "web-search",
            Version:     "1.0.0",
            Description: "搜索互联网内容",
            Tags:        []string{"search", "web"},
            Timeout:     30 * time.Second,
        },
        client: initSearchClient(),
    }
    return globalRegistry.Register(skill)
}
```

### 阶段 5: DEPLOY (部署)

部署检查清单：

- [ ] 配置文件已准备
- [ ] API 密钥等敏感信息已配置 (环境变量/Secret Manager)
- [ ] 日志收集已配置
- [ ] 监控告警已配置
- [ ] 回滚方案已准备

### 阶段 6: ACTIVE (运行)

运行时监控指标：

```go
type SkillMetrics struct {
    TotalCalls      int64   `json:"total_calls"`
    SuccessfulCalls int64   `json:"successful_calls"`
    FailedCalls     int64   `json:"failed_calls"`
    AverageLatency  float64 `json:"average_latency_ms"`
    P99Latency      float64 `json:"p99_latency_ms"`
    ErrorRate       float64 `json:"error_rate"`
}
```

### 阶段 7: UPDATE (更新)

版本号规范 (语义化版本)：

```
v<MAJOR>.<MINOR>.<PATCH>
```

| 变更类型 | 版本号变化 | 说明 |
|----------|------------|------|
| 不兼容的 API 修改 | MAJOR +1 | 需要调用方适配 |
| 向后兼容的功能新增 | MINOR +1 | 调用方可选升级 |
| 向后兼容的 Bug 修复 | PATCH +1 | 建议所有调用方升级 |

### 阶段 8: DEPRECATE (弃用)

```go
func (s *Skill) Meta() SkillMeta {
    meta := s.meta
    meta.Deprecated = true
    meta.DeprecationMessage = "请使用 v2.search 替代。此版本将于 2025-06-01 移除。"
    meta.SupersededBy = "v2.search"
    return meta
}
```

弃用时间线：

- **Day 0**: 标记为 Deprecated，日志记录警告
- **Day 30**: 通知所有活跃调用方
- **Day 60**: 限制调用频率
- **Day 90**: 完全移除

### 阶段 9: RETIRE (退役)

```go
func RetireSkill(name string) error {
    if active := getActiveCallCount(name); active > 0 {
        return fmt.Errorf("skill %s has %d active calls", name, active)
    }
    if err := globalRegistry.Unregister(name); err != nil {
        return err
    }
    archiveSkillData(name)
    cleanupResources(name)
    return nil
}
```

## 下一步

- 阅读 [04-plugin-development.md](04-plugin-development.md) 了解插件开发
