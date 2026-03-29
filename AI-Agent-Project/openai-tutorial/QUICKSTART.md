# 快速开始指南

## 5 分钟快速上手

### 步骤 1: 安装依赖

```bash
cd openai-tutorial
pip install -r requirements.txt
```

### 步骤 2: 配置 API Key

```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑 .env 文件，填入你的 API Key
# OPENAI_API_KEY=sk-your-api-key-here
```

或者直接在终端设置：

```bash
export OPENAI_API_KEY='sk-your-api-key-here'
```

### 步骤 3: 运行第一个示例

```bash
# 基础示例
python 01-基础入门/hello_world.py

# 综合示例
python examples/comprehensive_examples.py

# 工具函数示例
python examples/utils.py
```

## 学习路线

### 📌 Day 1: 基础入门
- [ ] 阅读 [01-基础入门](01-基础入门/README.md)
- [ ] 运行 hello_world.py
- [ ] 理解 API Key 管理
- [ ] 学习错误处理

### 📌 Day 2: 核心 API
- [ ] 阅读 [02-核心 API 使用](02-核心 API 使用/README.md)
- [ ] 练习流式输出
- [ ] 实现 Function Calling
- [ ] 尝试 Embeddings

### 📌 Day 3: Agent 开发
- [ ] 阅读 [03-Agent 开发实战](03-Agent 开发实战/README.md)
- [ ] 运行 simple_agent.py
- [ ] 创建自己的 Agent
- [ ] 添加工具支持

### 📌 Day 4: 进阶技巧
- [ ] 阅读 [04-进阶技巧](04-进阶技巧/README.md)
- [ ] 实现异步编程
- [ ] 添加缓存机制
- [ ] 优化 Token 使用

### 📌 Day 5: 最佳实践
- [ ] 阅读 [05-最佳实践](05-最佳实践/README.md)
- [ ] 重构代码结构
- [ ] 完善错误处理
- [ ] 添加监控日志

## 常见问题快速解决

### 问题 1: 导入错误
```bash
# ModuleNotFoundError: No module named 'openai'
pip install -U openai
```

### 问题 2: API Key 无效
```bash
# 检查环境变量
echo $OPENAI_API_KEY

# 重新设置
export OPENAI_API_KEY='sk-...'
```

### 问题 3: 连接超时
```python
# 增加超时时间
client = OpenAI(timeout=60.0)
```

## 获取帮助

1. **查看文档**: 每个目录下的 README.md
2. **运行示例**: examples/ 目录中的完整示例
3. **查看 FAQ**: [06-常见问题](06-常见问题/README.md)
4. **官方文档**: https://platform.openai.com/docs

## 推荐工具

### 开发工具
- **VS Code**: Python 扩展
- **Jupyter Notebook**: 交互式学习
- **Postman**: API 测试

### 调试工具
- **pdb**: Python 调试器
- **logging**: 日志记录
- **tiktoken**: Token 计算

## 下一步

完成快速开始后，按照顺序系统学习各个章节，或根据需求跳转到感兴趣的部分！

祝你学习愉快！🚀
