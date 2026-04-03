# Go + Redis 实战教程 (面试向)

本目录用于系统学习 Go 与 Redis 的工程化交互方式，目标是覆盖后端面试中常见的实操题和原理题。

## 学习目标

- 熟悉 Go 客户端 `go-redis/v9` 的连接、超时、重试和错误处理。
- 掌握常见数据结构操作：String、Hash、List、Set、ZSet、Stream。
- 理解高频工程能力：Pipeline、事务、Lua 分布式锁、缓存穿透防护。
- 能够回答 Redis 原理问题：数据结构、持久化、淘汰策略、主从和集群。

## 目录结构

- `tutorial/00_env_and_connect`：环境准备与连接 Redis
- `tutorial/01_string_hash`：String / Hash 基础操作
- `tutorial/02_list_set_zset`：List / Set / ZSet 场景化示例
- `tutorial/03_pipeline_tx`：Pipeline 与事务
- `tutorial/04_lock_and_cache`：分布式锁与缓存模式
- `tutorial/05_stream`：Stream 与消费组
- `tutorial/06_redis_cli_commands`：Redis 命令行教程（与 Go 无关）
- `docs/redis_knowledge_map.md`：Redis 核心知识图谱
- `docs/interview_qna.md`：Go + Redis 高频面试问答

## 运行前准备

1. 启动 Redis 服务（本地默认 `127.0.0.1:6379`）。
2. 在本仓库 `go` 目录执行：

```bash
go mod tidy
```

3. 可通过环境变量覆盖连接参数：

```bash
export REDIS_ADDR=127.0.0.1:6379
export REDIS_PASSWORD=
export REDIS_DB=0
```

## 运行方式

在 `go` 目录下执行（每个子目录可独立运行）：

```bash
go run ./redis/tutorial/00_env_and_connect
go run ./redis/tutorial/01_string_hash
go run ./redis/tutorial/02_list_set_zset
go run ./redis/tutorial/03_pipeline_tx
go run ./redis/tutorial/04_lock_and_cache
go run ./redis/tutorial/05_stream
```

命令行教程不需要运行 Go 代码，请直接阅读：

```text
redis/tutorial/06_redis_cli_commands/README.md
redis/tutorial/06_redis_cli_commands/hands_on_lab.md
redis/tutorial/06_redis_cli_commands/interview_drills.md
```

## 面试准备建议

- 先跑代码，再读子目录 README，最后读 `docs` 下的知识文档。
- 面试回答建议采用三段式：业务场景 -> 技术方案 -> 风险与优化。
- 对每个功能至少准备一个扩展问题（例如分布式锁如何防误删、事务为什么不回滚）。
