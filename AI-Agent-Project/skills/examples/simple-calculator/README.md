# Simple Calculator Skill

入门级 Skill 示例，演示如何创建一个基础的四则运算技能。

## 功能

- 加法、减法、乘法、除法
- 输入参数校验
- 除零错误处理
- 结构化错误返回

## 学习要点

| 知识点 | 说明 |
|--------|------|
| Skill Manifest | 最简 skill.yaml 配置 |
| Handler 接口 | 实现 `Handle` 方法 |
| 参数校验 | 输入合法性检查 |
| 错误处理 | SkillError 结构化错误 |
| 单元测试 | table-driven 测试模式 |

## 快速开始

```bash
# 运行测试
go test ./...

# 运行示例
go run main.go
```

## 项目结构

```
simple-calculator/
├── README.md
├── skill.yaml        # Skill 清单文件
├── handler.go        # 核心处理逻辑
├── handler_test.go   # 单元测试
└── main.go           # 运行入口
```
