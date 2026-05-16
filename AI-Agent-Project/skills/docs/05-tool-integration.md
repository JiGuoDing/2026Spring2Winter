# 05 - 工具集成

## 学习目标

- 理解如何为 Skill 集成外部工具
- 掌握 API 调用、数据库访问和文件系统操作的安全封装
- 学习工具调用的重试与容错策略

## 工具集成的核心原则

| 原则 | 说明 |
|------|------|
| 最小权限 | 只请求必要的权限和访问范围 |
| 故障隔离 | 外部工具故障不应导致 Skill 崩溃 |
| 超时控制 | 所有外部调用必须设置超时 |
| 可观测性 | 所有外部调用必须有日志和指标 |
| 幂等重试 | 重试逻辑需保证幂等性 |

## HTTP 工具集成

### 封装 HTTP Client

```go
type HTTPTool struct {
    client      *http.Client
    retryMax    int
    retryDelay  time.Duration
    rateLimiter *rate.Limiter
}

func NewHTTPTool(timeout time.Duration, maxRetries int) *HTTPTool {
    return &HTTPTool{
        client: &http.Client{
            Timeout: timeout,
            Transport: &http.Transport{
                MaxIdleConns:        100,
                MaxIdleConnsPerHost: 10,
                IdleConnTimeout:     90 * time.Second,
            },
        },
        retryMax:   maxRetries,
        retryDelay: 500 * time.Millisecond,
        rateLimiter: rate.NewLimiter(rate.Every(100*time.Millisecond), 10),
    }
}

func (h *HTTPTool) Do(req *http.Request) (*http.Response, error) {
    if err := h.rateLimiter.Wait(req.Context()); err != nil {
        return nil, fmt.Errorf("rate limit: %w", err)
    }

    var lastErr error
    for attempt := 0; attempt <= h.retryMax; attempt++ {
        if attempt > 0 {
            delay := h.retryDelay * time.Duration(1<<(attempt-1))
            select {
            case <-req.Context().Done():
                return nil, req.Context().Err()
            case <-time.After(delay):
            }
        }

        resp, err := h.client.Do(req.Clone(req.Context()))
        if err != nil {
            lastErr = err
            continue
        }

        if resp.StatusCode >= 500 {
            lastErr = fmt.Errorf("server error: %d", resp.StatusCode)
            resp.Body.Close()
            continue
        }

        return resp, nil
    }
    return nil, fmt.Errorf("after %d retries: %w", h.retryMax, lastErr)
}
```

## 数据库工具集成

```go
type DBTool struct {
    db     *sql.DB
    maxOpen int
}

func NewDBTool(dsn string, maxOpenConns int) (*DBTool, error) {
    db, err := sql.Open("postgres", dsn)
    if err != nil {
        return nil, err
    }
    db.SetMaxOpenConns(maxOpenConns)
    db.SetMaxIdleConns(maxOpenConns / 2)
    db.SetConnMaxLifetime(5 * time.Minute)

    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
    defer cancel()
    if err := db.PingContext(ctx); err != nil {
        return nil, fmt.Errorf("db ping: %w", err)
    }

    return &DBTool{db: db, maxOpen: maxOpenConns}, nil
}

func (d *DBTool) Query(ctx context.Context, query string, args ...interface{}) ([]map[string]interface{}, error) {
    rows, err := d.db.QueryContext(ctx, query, args...)
    if err != nil {
        return nil, fmt.Errorf("query: %w", err)
    }
    defer rows.Close()

    cols, _ := rows.Columns()
    var results []map[string]interface{}

    for rows.Next() {
        values := make([]interface{}, len(cols))
        ptrs := make([]interface{}, len(cols))
        for i := range values {
            ptrs[i] = &values[i]
        }
        if err := rows.Scan(ptrs...); err != nil {
            return nil, err
        }
        row := make(map[string]interface{})
        for i, col := range cols {
            row[col] = values[i]
        }
        results = append(results, row)
    }
    return results, nil
}

func (d *DBTool) Close() error {
    return d.db.Close()
}
```

## 缓存工具集成

```go
type CacheTool struct {
    store map[string]cacheEntry
    mu    sync.RWMutex
    ttl   time.Duration
}

type cacheEntry struct {
    value     json.RawMessage
    expiresAt time.Time
}

func NewCacheTool(ttl time.Duration) *CacheTool {
    c := &CacheTool{
        store: make(map[string]cacheEntry),
        ttl:   ttl,
    }
    go c.cleanupLoop()
    return c
}

func (c *CacheTool) Get(key string) (json.RawMessage, bool) {
    c.mu.RLock()
    defer c.mu.RUnlock()

    entry, exists := c.store[key]
    if !exists || time.Now().After(entry.expiresAt) {
        return nil, false
    }
    return entry.value, true
}

func (c *CacheTool) Set(key string, value json.RawMessage) {
    c.mu.Lock()
    defer c.mu.Unlock()

    c.store[key] = cacheEntry{
        value:     value,
        expiresAt: time.Now().Add(c.ttl),
    }
}

func (c *CacheTool) cleanupLoop() {
    ticker := time.NewTicker(time.Minute)
    for range ticker.C {
        c.mu.Lock()
        now := time.Now()
        for k, v := range c.store {
            if now.After(v.expiresAt) {
                delete(c.store, k)
            }
        }
        c.mu.Unlock()
    }
}
```

## 工具注册与发现

```go
type ToolRegistry struct {
    tools map[string]Tool
    mu    sync.RWMutex
}

type Tool interface {
    Name() string
    Type() string
    HealthCheck(ctx context.Context) error
    Close() error
}

func (tr *ToolRegistry) Register(tool Tool) {
    tr.mu.Lock()
    defer tr.mu.Unlock()
    tr.tools[tool.Name()] = tool
}

func (tr *ToolRegistry) Get(name string) (Tool, bool) {
    tr.mu.RLock()
    defer tr.mu.RUnlock()
    t, ok := tr.tools[name]
    return t, ok
}
```

## 下一步

- 阅读 [06-testing-and-debugging.md](06-testing-and-debugging.md) 了解测试与调试
