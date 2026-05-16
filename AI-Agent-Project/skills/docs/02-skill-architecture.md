# 02 - 技能架构设计

## 学习目标

- 理解 AI Agent 技能的层级架构
- 掌握技能组件之间的交互关系
- 了解技能注册与发现机制

## 整体架构

```
┌─────────────────────────────────────────────────┐
│                   Agent 核心                     │
│  ┌───────────┐  ┌───────────┐  ┌────────────┐  │
│  │ 意图识别   │  │ 任务规划   │  │ 记忆管理    │  │
│  └─────┬─────┘  └─────┬─────┘  └─────┬──────┘  │
│        └──────┬───────┴───────┬──────┘          │
│        ┌──────▼───────────────▼──────┐          │
│        │       Skill Registry        │          │
│        │  (技能注册与发现中心)         │          │
│        └──────┬───────────────┬──────┘          │
│   ┌───────────▼───┐   ┌───────▼───────────┐    │
│   │  Skill Pool    │   │  Plugin Manager   │    │
│   └───────┬───────┘   └───────┬───────────┘    │
│   ┌───────▼───────────────────▼───────────┐     │
│   │          Skill Executor               │     │
│   │  (沙箱执行、超时控制、资源限制)         │     │
│   └───────────────────────────────────────┘     │
└─────────────────────────────────────────────────┘
```

## 技能组件详解

### 1. Skill Manifest (技能清单)

每个 Skill 必须包含清单文件，描述其基本属性：

```yaml
name: web-search
version: 1.2.0
author: "Team Search"
description: "搜索互联网内容并返回摘要"
tags: ["search", "web", "utility"]

input_schema:
  type: object
  properties:
    query:
      type: string
      description: "搜索关键词"
      minLength: 1
      maxLength: 500
    max_results:
      type: integer
      description: "最大结果数"
      default: 10
      minimum: 1
      maximum: 50
  required:
    - query

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

timeout_ms: 30000
retry:
  max_attempts: 3
  backoff: exponential
```

### 2. Skill Registry (技能注册表)

Registry 是技能发现和管理的核心组件：

```go
type SkillRegistry struct {
    skills map[string]Skill
    mu     sync.RWMutex
}

func (r *SkillRegistry) Register(skill Skill) error {
    r.mu.Lock()
    defer r.mu.Unlock()
    if _, exists := r.skills[skill.Name()]; exists {
        return fmt.Errorf("skill %s already registered", skill.Name())
    }
    r.skills[skill.Name()] = skill
    return nil
}

func (r *SkillRegistry) Get(name string) (Skill, error) {
    r.mu.RLock()
    defer r.mu.RUnlock()
    skill, exists := r.skills[name]
    if !exists {
        return nil, fmt.Errorf("skill %s not found", name)
    }
    return skill, nil
}

func (r *SkillRegistry) List() []SkillMeta {
    r.mu.RLock()
    defer r.mu.RUnlock()
    var metas []SkillMeta
    for _, s := range r.skills {
        metas = append(metas, s.Meta())
    }
    return metas
}

func (r *SkillRegistry) SearchByTag(tag string) []SkillMeta {
    r.mu.RLock()
    defer r.mu.RUnlock()
    var metas []SkillMeta
    for _, s := range r.skills {
        for _, t := range s.Meta().Tags {
            if t == tag {
                metas = append(metas, s.Meta())
                break
            }
        }
    }
    return metas
}
```

### 3. Skill Executor (技能执行器)

执行器提供统一的安全执行环境：

```go
type SkillExecutor struct {
    registry   *SkillRegistry
    timeout    time.Duration
    maxRetries int
}

type SkillResult struct {
    SkillName string
    Output    json.RawMessage
    Duration  time.Duration
    Retries   int
}

func (e *SkillExecutor) Execute(name string, input json.RawMessage) (*SkillResult, error) {
    skill, err := e.registry.Get(name)
    if err != nil {
        return nil, err
    }

    ctx, cancel := context.WithTimeout(context.Background(), e.timeout)
    defer cancel()

    var lastErr error
    for attempt := 0; attempt <= e.maxRetries; attempt++ {
        resultCh := make(chan *SkillResult, 1)
        errCh := make(chan error, 1)

        go func() {
            start := time.Now()
            output, err := skill.Handle(ctx, input)
            if err != nil {
                errCh <- err
                return
            }
            resultCh <- &SkillResult{
                SkillName: name,
                Output:    output,
                Duration:  time.Since(start),
                Retries:   attempt,
            }
        }()

        select {
        case result := <-resultCh:
            return result, nil
        case err := <-errCh:
            lastErr = err
            if attempt < e.maxRetries {
                time.Sleep(time.Duration(attempt+1) * 500 * time.Millisecond)
            }
        case <-ctx.Done():
            return nil, fmt.Errorf("skill %s execution timeout after %v", name, e.timeout)
        }
    }
    return nil, fmt.Errorf("skill %s failed after %d retries: %w", name, e.maxRetries, lastErr)
}
```

### 4. Plugin Manager (插件管理器)

支持动态加载和卸载技能插件：

```go
type PluginManager struct {
    plugins  map[string]*Plugin
    mu       sync.RWMutex
    registry *SkillRegistry
}

func (pm *PluginManager) Load(path string) error {
    plugin, err := loadPlugin(path)
    if err != nil {
        return fmt.Errorf("load plugin: %w", err)
    }

    pm.mu.Lock()
    pm.plugins[plugin.Name] = plugin
    pm.mu.Unlock()

    for _, skill := range plugin.Skills {
        if err := pm.registry.Register(skill); err != nil {
            return err
        }
    }
    return nil
}

func (pm *PluginManager) Unload(name string) error {
    pm.mu.Lock()
    plugin, exists := pm.plugins[name]
    pm.mu.Unlock()

    if !exists {
        return fmt.Errorf("plugin %s not found", name)
    }

    for _, skill := range plugin.Skills {
        pm.registry.Unregister(skill.Name())
    }
    return nil
}
```

## 技能间通信模式

### 模式 1: 管道 (Pipeline)

```
Skill A → Skill B → Skill C
```

输出依次作为下一技能的输入，适合顺序处理流程。

### 模式 2: 扇出/扇入 (Fan-out/Fan-in)

```
         ┌── Skill B
Skill A ─┼── Skill C ── Skill E
         └── Skill D
```

并行执行多个技能，聚合结果后传递给下游。

### 模式 3: 路由 (Router)

```
               ┌── Skill B
Skill A ── Router ──┼── Skill C
               └── Skill D
```

根据运行时条件动态决定调用哪个技能。

## 安全性设计

| 层面 | 策略 | 说明 |
|------|------|------|
| 输入校验 | JSON Schema 验证 | 拒绝不符合 Schema 的输入 |
| 沙箱执行 | 资源限制 (CPU/内存/时间) | 防止单个技能耗尽系统资源 |
| 网络隔离 | 白名单机制 | 控制技能的网络访问范围 |
| 权限控制 | RBAC | 基于角色的技能访问控制 |
| 审计日志 | 全量记录 | 所有技能调用记录可追溯 |

## 下一步

- 阅读 [03-skill-lifecycle.md](03-skill-lifecycle.md) 了解技能生命周期管理
