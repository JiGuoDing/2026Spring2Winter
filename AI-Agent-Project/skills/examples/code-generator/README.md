# Code Generator Skill

高级 Skill 示例，演示如何开发一个代码生成技能，支持模板驱动的代码生成、语法校验和多语言输出。

## 功能

- 基于模板的代码生成
- 多语言支持（Go / Python / TypeScript）
- 语法校验与风格检查
- 变量替换与条件逻辑
- 生成结果缓存

## 学习要点

| 知识点 | 说明 |
|--------|------|
| 模板引擎 | Go text/template 驱动代码生成 |
| 多语言适配 | 统一接口 + 语言特定模板 |
| 语法校验 | 生成后自动校验 |
| 依赖注入 | 模板变量注入 |
| 缓存策略 | 相同输入复用生成结果 |

## 项目结构

```
code-generator/
├── README.md
├── skill.yaml        # Skill 清单
├── handler.go        # 生成处理器
├── templates.go      # 模板管理
├── validator.go      # 语法校验
├── handler_test.go   # 单元测试
└── main.go           # 运行入口
```
