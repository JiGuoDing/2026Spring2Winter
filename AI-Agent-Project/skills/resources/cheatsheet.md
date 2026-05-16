# Skill 开发速查表

## 快速创建新 Skill

```bash
# 1. 从模板创建
cp templates/skill-template.yaml    my-skill/skill.yaml
cp templates/handler-template.go    my-skill/handler.go
cp templates/test-template.go       my-skill/handler_test.go

# 2. 替换占位符
# {{SKILL_NAME}}      → 技能名称 (kebab-case)
# {{SKILL_DESCRIPTION}} → 技能描述
# {{HANDLER_NAME}}    → 处理器名称 (PascalCase)
# {{SKILL_TYPE}}      → compute / integration / orchestration / generate
# {{TAG_1}}, {{TAG_2}} → 分类标签

# 3. 运行测试
cd my-skill && go test ./...

# 4. 注册技能
# 更新 config/skill-registry.yaml
```

## skill.yaml 模板

```yaml
apiVersion: skill.agent/v1
kind: Skill
metadata:
  name: my-skill
  version: 1.0.0
  description: 技能描述
  author: your-name
  tags: [tag1, tag2]
spec:
  type: compute
  input:
    properties:
      param1: { type: string, description: 参数1 }
    required: [param1]
  output:
    properties:
      result: { type: string, description: 结果 }
    required: [result]
  config:
    timeout: 10s
    maxRetries: 2
```

## Handler 接口

```go
type MyHandler struct{}

func (h *MyHandler) Validate(input json.RawMessage) error {
    var in MyInput
    if err := json.Unmarshal(input, &in); err != nil {
        return &SkillError{Code: "INVALID_INPUT", Message: "解析失败", Detail: err.Error()}
    }
    return nil
}

func (h *MyHandler) Handle(input json.RawMessage) (json.RawMessage, error) {
    if err := h.Validate(input); err != nil {
        return nil, err
    }
    var in MyInput
    _ = json.Unmarshal(input, &in)
    output := MyOutput{/* ... */}
    return json.Marshal(output)
}
```

## SkillError 格式

```go
type SkillError struct {
    Code    string `json:"code"`       // 错误码: INVALID_INPUT, TIMEOUT, etc.
    Message string `json:"message"`     // 人类可读的错误消息
    Detail  string `json:"detail"`      // 详细信息（可选）
}
```

## 常用错误码

| 错误码 | 场景 |
|--------|------|
| `INVALID_INPUT` | 输入参数格式错误 |
| `MISSING_PARAM` | 缺少必填参数 |
| `TIMEOUT` | 执行超时 |
| `EXTERNAL_ERROR` | 外部服务调用失败 |
| `NOT_FOUND` | 资源不存在 |
| `PERMISSION_DENIED` | 权限不足 |
| `RATE_LIMITED` | 触发限流 |
| `INTERNAL_ERROR` | 内部错误 |

## 测试模板

```go
func TestMyHandler_Handle(t *testing.T) {
    handler := NewMyHandler()
    tests := []struct {
        name        string
        input       MyInput
        wantResult  string
        wantErrCode string
    }{
        {name: "成功场景", input: MyInput{Param1: "test"}, wantResult: "ok"},
        {name: "错误场景", input: MyInput{}, wantErrCode: "MISSING_PARAM"},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            inputJSON, _ := json.Marshal(tt.input)
            outputJSON, err := handler.Handle(inputJSON)
            if tt.wantErrCode != "" {
                var skillErr *SkillError
                if errors.As(err, &skillErr) && skillErr.Code != tt.wantErrCode {
                    t.Errorf("错误码 = %s, 期望 %s", skillErr.Code, tt.wantErrCode)
                }
                return
            }
            if err != nil { t.Fatalf("未期望错误: %v", err) }
            var output MyOutput
            json.Unmarshal(outputJSON, &output)
        })
    }
}
```

## 生命周期阶段

| 阶段 | 操作 | 产物 |
|------|------|------|
| CREATE | 需求分析、设计 | skill.yaml |
| BUILD | 编码实现 | handler.go |
| TEST | 单元/集成测试 | handler_test.go |
| REGISTER | 注册到 Registry | registry entry |
| DEPLOY | 部署上线 | 运行实例 |
| ACTIVE | 正常服务 | 监控指标 |
| UPDATE | 版本升级 | 新版本 |
| DEPRECATE | 标记废弃 | 废弃通知 |
| RETIRE | 下线移除 | 归档记录 |

## 性能优化清单

- [ ] 设置超时 (context.WithTimeout)
- [ ] 连接复用 (http.Client 连接池)
- [ ] 批量处理 (减少 I/O 次数)
- [ ] 缓存热点数据 (MemoryCache + TTL)
- [ ] 并发执行独立任务 (goroutine + WaitGroup)
- [ ] 限流保护 (rate.Limiter)
- [ ] 指标埋点 (Prometheus)

## 安全检查清单

- [ ] 输入校验 (Validate 方法)
- [ ] 输出脱敏 (敏感字段掩码)
- [ ] SQL 注入防护 (参数化查询)
- [ ] XSS 防护 (HTML 转义)
- [ ] 不记录敏感数据
- [ ] 最小权限原则
- [ ] HTTPS 通信
