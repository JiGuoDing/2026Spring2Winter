# Data Analysis Skill

中级 Skill 示例，演示如何开发一个数据分析技能，支持数据清洗、统计计算和图表生成。

## 功能

- CSV/JSON 数据导入
- 数据清洗（去重、填充缺失值、异常值过滤）
- 统计分析（均值、中位数、标准差、相关系数）
- 数据管道 (Pipeline) 模式
- 结果导出为 JSON

## 学习要点

| 知识点 | 说明 |
|--------|------|
| 数据管道 | Pipeline 模式组织处理步骤 |
| 中间件 | 可插拔的数据处理步骤 |
| 泛型处理 | 支持多种数据格式 |
| 统计计算 | 基础统计指标实现 |
| 批处理 | 大数据集分批处理 |

## 项目结构

```
data-analysis/
├── README.md
├── skill.yaml       # Skill 清单
├── handler.go       # 分析处理器
├── pipeline.go      # 数据管道
├── stats.go         # 统计计算
├── handler_test.go  # 单元测试
└── main.go          # 运行入口
```
