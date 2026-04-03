# 00 环境与连接

## 你会学到什么

- 如何在 Go 中初始化 Redis 客户端。
- 如何通过环境变量切换地址、密码、DB。
- 如何做最基础的 Ping / Set / Get 验证。

## 运行

在 `go` 目录执行：

```bash
go run ./redis/tutorial/00_env_and_connect
```

## 对应面试问题

- 你如何管理 Redis 连接参数？
- 为什么要配置连接超时、读写超时？
- 为什么 Redis 客户端应复用而不是每次请求新建？
