# 04 - 插件开发

## 学习目标

- 理解插件与技能的关系
- 掌握插件的开发规范
- 实现一个可动态加载的插件

## 插件与技能的关系

```
Plugin (插件)
  ├── Skill A (技能)
  ├── Skill B (技能)
  ├── 共享配置
  └── 依赖声明
```

一个 Plugin 可以包含多个相关的 Skill，它们共享配置和依赖。Plugin 是技能的打包和分发单元。

## 插件目录结构

```
my-plugin/
├── plugin.yaml              # 插件清单
├── skills/
│   ├── skill-a/
│   │   ├── skill.yaml       # 技能定义
│   │   └── handler.go       # 处理器
│   └── skill-b/
│       ├── skill.yaml
│       └── handler.go
├── shared/
│   ├── config.go            # 共享配置
│   └── utils.go             # 工具函数
├── go.mod
└── go.sum
```

## plugin.yaml 清单

```yaml
name: search-tools
version: 1.0.0
author: "Search Team"
description: "搜索工具集插件，包含网页搜索、图片搜索和新闻搜索"

skills:
  - name: web-search
    handler: skills/web-search/handler.go
  - name: image-search
    handler: skills/image-search/handler.go
  - name: news-search
    handler: skills/news-search/handler.go

dependencies:
  - name: http-client
    version: ">=1.0.0"
  - name: cache
    version: ">=2.0.0"

permissions:
  - network.outbound
  - filesystem.read:/tmp/cache

config:
  api_key:
    type: string
    required: true
    description: "Search API key"
    secret: true
  cache_ttl:
    type: integer
    default: 300
    description: "Cache TTL in seconds"
```

## 插件接口实现

```go
package plugin

type Plugin interface {
    Name() string
    Version() string
    Skills() []Skill
    Init(config map[string]interface{}) error
    Shutdown() error
}

type BasePlugin struct {
    name    string
    version string
    skills  []Skill
    config  map[string]interface{}
}

func (p *BasePlugin) Name() string    { return p.name }
func (p *BasePlugin) Version() string { return p.version }
func (p *BasePlugin) Skills() []Skill { return p.skills }

func (p *BasePlugin) Init(config map[string]interface{}) error {
    p.config = config
    for _, skill := range p.skills {
        if initializable, ok := skill.(Initializable); ok {
            if err := initializable.Init(config); err != nil {
                return fmt.Errorf("init skill %s: %w", skill.Name(), err)
            }
        }
    }
    return nil
}

func (p *BasePlugin) Shutdown() error {
    for _, skill := range p.skills {
        if shutdownable, ok := skill.(Shutdownable); ok {
            if err := shutdownable.Shutdown(); err != nil {
                log.Printf("shutdown skill %s: %v", skill.Name(), err)
            }
        }
    }
    return nil
}
```

## 完整插件示例: 搜索工具集

```go
package main

import (
    "context"
    "encoding/json"
    "fmt"
    "net/http"
    "time"
)

type SearchPlugin struct {
    BasePlugin
    httpClient *http.Client
    apiKey     string
    cacheTTL   int
}

func NewSearchPlugin() *SearchPlugin {
    p := &SearchPlugin{}
    p.name = "search-tools"
    p.version = "1.0.0"

    p.skills = []Skill{
        &WebSearchSkill{plugin: p},
        &ImageSearchSkill{plugin: p},
    }
    return p
}

func (p *SearchPlugin) Init(config map[string]interface{}) error {
    apiKey, ok := config["api_key"].(string)
    if !ok || apiKey == "" {
        return fmt.Errorf("api_key is required")
    }
    p.apiKey = apiKey

    p.cacheTTL = 300
    if ttl, ok := config["cache_ttl"].(int); ok {
        p.cacheTTL = ttl
    }

    p.httpClient = &http.Client{Timeout: 10 * time.Second}
    return nil
}

type WebSearchSkill struct {
    plugin *SearchPlugin
}

func (s *WebSearchSkill) Name() string { return "web-search" }
func (s *WebSearchSkill) Meta() SkillMeta {
    return SkillMeta{
        Name:        "web-search",
        Version:     "1.0.0",
        Description: "搜索互联网内容",
        Tags:        []string{"search", "web"},
        Timeout:     10 * time.Second,
    }
}

func (s *WebSearchSkill) Validate(input json.RawMessage) error {
    var in struct {
        Query string `json:"query"`
    }
    if err := json.Unmarshal(input, &in); err != nil {
        return err
    }
    if in.Query == "" {
        return fmt.Errorf("query is required")
    }
    return nil
}

func (s *WebSearchSkill) Handle(ctx context.Context, input json.RawMessage) (json.RawMessage, error) {
    var in struct {
        Query      string `json:"query"`
        MaxResults int    `json:"max_results"`
    }
    if err := json.Unmarshal(input, &in); err != nil {
        return nil, err
    }
    if in.MaxResults == 0 {
        in.MaxResults = 10
    }

    results, err := s.plugin.searchWeb(ctx, in.Query, in.MaxResults)
    if err != nil {
        return nil, err
    }
    return json.Marshal(map[string]interface{}{"results": results})
}

func (s *WebSearchSkill) HealthCheck(ctx context.Context) error {
    return nil
}

type ImageSearchSkill struct{ plugin *SearchPlugin }

func (s *ImageSearchSkill) Name() string        { return "image-search" }
func (s *ImageSearchSkill) Meta() SkillMeta      { return SkillMeta{Name: "image-search", Version: "1.0.0", Description: "搜索图片", Tags: []string{"search", "image"}} }
func (s *ImageSearchSkill) Validate(input json.RawMessage) error { return nil }
func (s *ImageSearchSkill) Handle(ctx context.Context, input json.RawMessage) (json.RawMessage, error) {
    return json.Marshal(map[string]interface{}{"results": []string{}})
}
func (s *ImageSearchSkill) HealthCheck(ctx context.Context) error { return nil }

func (p *SearchPlugin) searchWeb(ctx context.Context, query string, max int) ([]map[string]string, error) {
    // 实际实现会调用搜索 API
    return []map[string]string{
        {"title": "Example Result", "url": "https://example.com", "snippet": "An example search result"},
    }, nil
}
```

## 插件加载与热更新

```go
func LoadPluginFromPath(path string, registry *SkillRegistry) error {
    configData, err := os.ReadFile(filepath.Join(path, "plugin.yaml"))
    if err != nil {
        return err
    }

    var manifest PluginManifest
    if err := yaml.Unmarshal(configData, &manifest); err != nil {
        return err
    }

    plugin, err := buildPlugin(manifest, path)
    if err != nil {
        return err
    }

    envConfig := loadConfigFromEnv(manifest.Name)
    if err := plugin.Init(envConfig); err != nil {
        return fmt.Errorf("plugin init: %w", err)
    }

    for _, skill := range plugin.Skills() {
        if err := registry.Register(skill); err != nil {
            return fmt.Errorf("register skill %s: %w", skill.Name(), err)
        }
    }

    log.Printf("plugin %s v%s loaded with %d skills", plugin.Name(), plugin.Version(), len(plugin.Skills()))
    return nil
}
```

## 下一步

- 阅读 [05-tool-integration.md](05-tool-integration.md) 了解工具集成
