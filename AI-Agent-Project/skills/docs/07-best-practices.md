# 07 - 最佳实践

## 学习目标

- 掌握 Skill 开发的业界最佳实践
- 了解常见反模式及其规避方法
- 建立高质量的技能开发习惯

## 设计最佳实践

### 1. 单一职责原则

每个 Skill 应该只解决一个明确的问题。

**反面模式:**

```yaml
name: super-tool
description: "搜索网页、分析数据、生成报告、发送邮件"
```

**推荐做法:**

```yaml
name: web-search
description: "搜索互联网内容并返回结果"
```

### 2. 契约先行 (Contract First)

先定义输入输出 Schema，再实现逻辑。

```yaml
input_schema:
  type: object
  properties:
    query:
      type: string
      minLength: 1
      maxLength: 1000
      description: "搜索关键词"
  required:
    - query
  additionalProperties: false

output_schema:
  type: object
  properties:
    results:
      type: array
      items:
        type: object
        properties:
          title: { type: string }
          url: { type: string, format: uri }
          snippet: { type: string }
        required: [title, url]
        additionalProperties: false
  required:
    - results
  additionalProperties: false
```

### 3. 防御性编程

```go
func (s *MySkill) Handle(ctx context.Context, input json.RawMessage) (json.RawMessage, error) {
    if len(input) == 0 {
        return nil, fmt.Errorf("input is empty")
    }

    if err := s.Validate(input); err != nil {
        return nil, fmt.Errorf("validation failed: %w", err)
    }

    var in MyInput
    if err := json.Unmarshal(input, &in); err != nil {
        return nil, fmt.Errorf("invalid JSON: %w", err)
    }

    select {
    case <-ctx.Done():
        return nil, ctx.Err()
    default:
    }

    output, err := s.process(ctx, in)
    if err != nil {
        return nil, fmt.Errorf("processing failed: %w", err)
    }

    result, err := json.Marshal(output)
    if err != nil {
        return nil, fmt.Errorf("marshal failed: %w", err)
    }

    return result, nil
}
```

## 性能最佳实践

### 1. 合理设置超时

```go
var defaultTimeouts = map[string]time.Duration{
    "local-calculation": 5 * time.Second,
    "database-query":    10 * time.Second,
    "api-call":          30 * time.Second,
    "file-operation":    60 * time.Second,
    "llm-inference":     120 * time.Second,
}
```

### 2. 连接复用

```go
var sharedHTTPClient = &http.Client{
    Transport: &http.Transport{
        MaxIdleConns:        100,
        MaxIdleConnsPerHost: 10,
        IdleConnTimeout:     90 * time.Second,
    },
    Timeout: 30 * time.Second,
}
```

### 3. 批量处理

```go
type BatchProcessor struct {
    batchSize int
    batchTimeout time.Duration
}

func (bp *BatchProcessor) Process(items []Item) ([]Result, error) {
    var results []Result
    for i := 0; i < len(items); i += bp.batchSize {
        end := i + bp.batchSize
        if end > len(items) {
            end = len(items)
        }
        batch := items[i:end]
        batchResults, err := bp.processBatch(batch)
        if err != nil {
            return nil, err
        }
        results = append(results, batchResults...)
    }
    return results, nil
}
```

## 安全最佳实践

### 1. 敏感信息处理

```go
func loadSecureConfig() (map[string]string, error) {
    config := make(map[string]string)

    if apiKey := os.Getenv("SKILL_API_KEY"); apiKey != "" {
        config["api_key"] = apiKey
    } else {
        return nil, fmt.Errorf("SKILL_API_KEY environment variable not set")
    }

    return config, nil
}
```

### 2. 输入净化

```go
func sanitizeInput(input string) string {
    return strings.TrimSpace(
        html.UnescapeString(
            stripTags(input),
        ),
    )
}
```

### 3. 输出脱敏

```go
func maskSensitiveData(data map[string]interface{}) map[string]interface{} {
    sensitiveFields := map[string]bool{"api_key": true, "password": true, "token": true, "secret": true}
    masked := make(map[string]interface{})
    for k, v := range data {
        if sensitiveFields[k] {
            masked[k] = "***REDACTED***"
        } else {
            masked[k] = v
        }
    }
    return masked
}
```

## 错误处理最佳实践

### 结构化错误

```go
type SkillError struct {
    Code    string `json:"code"`
    Message string `json:"message"`
    Detail  string `json:"detail,omitempty"`
    Retry   bool   `json:"retryable"`
}

func (e *SkillError) Error() string {
    return fmt.Sprintf("[%s] %s: %s", e.Code, e.Message, e.Detail)
}

var (
    ErrInvalidInput = &SkillError{Code: "INVALID_INPUT", Message: "输入参数无效", Retry: false}
    ErrTimeout      = &SkillError{Code: "TIMEOUT", Message: "执行超时", Retry: true}
    ErrRateLimit    = &SkillError{Code: "RATE_LIMIT", Message: "请求频率超限", Retry: true}
    ErrUpstream     = &SkillError{Code: "UPSTREAM_ERROR", Message: "上游服务异常", Retry: true}
)
```

## 可观测性最佳实践

### 指标采集

```go
type SkillInstrumentation struct {
    callCounter    prometheus.Counter
    latencyHist    prometheus.Histogram
    errorCounter   prometheus.Counter
}

func NewSkillInstrumentation(skillName string) *SkillInstrumentation {
    return &SkillInstrumentation{
        callCounter: prometheus.NewCounter(prometheus.CounterOpts{
            Name: "skill_calls_total",
            ConstLabels: prometheus.Labels{"skill": skillName},
        }),
        latencyHist: prometheus.NewHistogram(prometheus.HistogramOpts{
            Name: "skill_duration_seconds",
            ConstLabels: prometheus.Labels{"skill": skillName},
            Buckets: prometheus.DefBuckets,
        }),
        errorCounter: prometheus.NewCounter(prometheus.CounterOpts{
            Name: "skill_errors_total",
            ConstLabels: prometheus.Labels{"skill": skillName},
        }),
    }
}
```

## 常见反模式清单

| 反模式 | 问题 | 改进方案 |
|--------|------|----------|
| 万能 Skill | 职责不清，难以维护和测试 | 拆分为多个单一职责的 Skill |
| 硬编码配置 | 无法适应不同环境 | 使用配置文件和环境变量 |
| 忽略超时 | 外部调用可能永久阻塞 | 所有 I/O 操作设置超时 |
| 裸抛异常 | Agent 无法区分可重试错误 | 使用结构化 SkillError |
| 忽略 Context | 超时和取消信号无法传递 | 所有方法接收 ctx 参数 |
| 全局状态 | 并发安全隐患 | 使用依赖注入和局部状态 |
| 过度重试 | 可能加重上游负载 | 使用指数退避 + 最大重试次数 |
