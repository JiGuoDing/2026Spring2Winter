# 06 - 测试与调试

## 学习目标

- 掌握 Skill 的分层测试策略
- 学习 Mock 和 Stub 的使用方法
- 了解运行时调试和问题定位技巧

## 测试金字塔

```
        ┌──────────┐
        │  E2E 测试 │  少量：整体流程验证
        ├──────────┤
        │ 集成测试   │  中等：外部依赖交互
        ├──────────┤
        │ 单元测试   │  大量：核心逻辑验证
        └──────────┘
```

## 单元测试

### Handler 单元测试

```go
package calculator

import (
    "encoding/json"
    "testing"
)

func TestAddHandler(t *testing.T) {
    tests := []struct {
        name    string
        input   AddInput
        want    float64
        wantErr bool
    }{
        {"positive numbers", AddInput{A: 3, B: 5}, 8, false},
        {"negative numbers", AddInput{A: -3, B: -5}, -8, false},
        {"zero values", AddInput{A: 0, B: 0}, 0, false},
        {"mixed signs", AddInput{A: -3, B: 5}, 2, false},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            input, _ := json.Marshal(tt.input)
            output, err := AddHandler(input)
            if (err != nil) != tt.wantErr {
                t.Fatalf("unexpected error: %v", err)
            }
            if !tt.wantErr {
                var result AddOutput
                json.Unmarshal(output, &result)
                if result.Value != tt.want {
                    t.Errorf("got %f, want %f", result.Value, tt.want)
                }
            }
        })
    }
}
```

### Schema 验证测试

```go
func TestInputValidation(t *testing.T) {
    schema := loadSchema("skill.yaml", "input")

    tests := []struct {
        name    string
        input   string
        valid   bool
    }{
        {"valid input", `{"query": "golang"}`, true},
        {"missing required field", `{"max_results": 10}`, false},
        {"empty query", `{"query": ""}`, false},
        {"invalid type", `{"query": 123}`, false},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            err := validateAgainstSchema(schema, []byte(tt.input))
            if (err == nil) != tt.valid {
                t.Errorf("validation result mismatch: valid=%v, err=%v", tt.valid, err)
            }
        })
    }
}
```

## Mock 与 Stub

### HTTP 服务 Mock

```go
type MockHTTPServer struct {
    server   *httptest.Server
    requests []CapturedRequest
    mu       sync.Mutex
}

type CapturedRequest struct {
    Method string
    Path   string
    Body   string
}

func NewMockHTTPServer(handler http.Handler) *MockHTTPServer {
    m := &MockHTTPServer{}
    m.server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        m.mu.Lock()
        body, _ := io.ReadAll(r.Body)
        m.requests = append(m.requests, CapturedRequest{
            Method: r.Method,
            Path:   r.URL.Path,
            Body:   string(body),
        })
        m.mu.Unlock()
        handler.ServeHTTP(w, r)
    }))
    return m
}

func (m *MockHTTPServer) URL() string { return m.server.URL }
func (m *MockHTTPServer) Close()      { m.server.Close() }

func (m *MockHTTPServer) GetRequests() []CapturedRequest {
    m.mu.Lock()
    defer m.mu.Unlock()
    return append([]CapturedRequest{}, m.requests...)
}

func TestWebSearchWithMock(t *testing.T) {
    mock := NewMockHTTPServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        json.NewEncoder(w).Encode(map[string]interface{}{
            "results": []map[string]string{
                {"title": "Mock Result", "url": "https://mock.example.com"},
            },
        })
    }))
    defer mock.Close()

    skill := &WebSearchSkill{baseURL: mock.URL()}
    input, _ := json.Marshal(map[string]interface{}{"query": "test"})
    output, err := skill.Handle(context.Background(), input)

    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }

    var result map[string]interface{}
    json.Unmarshal(output, &result)
    results := result["results"].([]interface{})
    if len(results) == 0 {
        t.Error("expected at least one result")
    }
}
```

## 集成测试

```go
func TestSkillIntegration(t *testing.T) {
    if testing.Short() {
        t.Skip("skipping integration test")
    }

    registry := NewSkillRegistry()
    executor := NewSkillExecutor(registry, 30*time.Second, 2)

    skill := NewWebSearchSkill(testAPIKey)
    registry.Register(skill)

    input, _ := json.Marshal(map[string]interface{}{
        "query":       "golang skills development",
        "max_results": 5,
    })

    result, err := executor.Execute("web-search", input)
    if err != nil {
        t.Fatalf("execution failed: %v", err)
    }

    if result.Duration > 5*time.Second {
        t.Errorf("execution too slow: %v", result.Duration)
    }
}
```

## 调试技巧

### 结构化日志

```go
type SkillLogger struct {
    skillName string
    logger    *slog.Logger
}

func (l *SkillLogger) LogExecution(input json.RawMessage, output json.RawMessage, duration time.Duration, err error) {
    attrs := []slog.Attr{
        slog.String("skill", l.skillName),
        slog.Duration("duration", duration),
    }
    if err != nil {
        attrs = append(attrs, slog.String("error", err.Error()))
        l.logger.LogAttrs(context.Background(), slog.LevelError, "skill execution failed", attrs...)
    } else {
        l.logger.LogAttrs(context.Background(), slog.LevelInfo, "skill execution completed", attrs...)
    }
}
```

### 性能分析

```go
func BenchmarkWebSearchSkill(b *testing.B) {
    skill := NewWebSearchSkill("test-key")
    input, _ := json.Marshal(map[string]interface{}{"query": "benchmark test"})

    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        _, err := skill.Handle(context.Background(), input)
        if err != nil {
            b.Fatal(err)
        }
    }
}
```

## 下一步

- 阅读 [07-best-practices.md](07-best-practices.md) 了解最佳实践
