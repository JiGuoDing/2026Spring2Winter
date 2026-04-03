package main

import (
	"context"
	"fmt"
	"os"
	"strconv"
	"time"

	"github.com/redis/go-redis/v9"
)

func main() {
	// 为本次演示设置总超时，避免网络异常时长时间阻塞。
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	// 初始化 Redis 客户端并在退出时释放连接池资源。
	rdb := newClient()
	defer rdb.Close()

	// 用 Ping 快速检测连接可用性。
	pong, err := rdb.Ping(ctx).Result()
	if err != nil {
		panic(fmt.Errorf("ping redis failed: %w", err))
	}
	fmt.Println("ping:", pong)

	// 写入一个带过期时间的测试 key。
	if err = rdb.Set(ctx, "tutorial:hello", "hello redis there", 30*time.Second).Err(); err != nil {
		panic(fmt.Errorf("set key failed: %w", err))
	}

	// 读取刚刚写入的 key，验证读写链路。
	val, err := rdb.Get(ctx, "tutorial:hello").Result()
	if err != nil {
		panic(fmt.Errorf("get key failed: %w", err))
	}
	fmt.Println("tutorial:hello =", val)
}

func newClient() *redis.Client {
	// 读取环境变量，方便在不同环境复用同一套代码。
	addr := getenv("REDIS_ADDR", "210.28.132.19:6397")
	password := getenv("REDIS_PASSWORD", "")
	db, err := strconv.Atoi(getenv("REDIS_DB", "0"))
	if err != nil {
		// 非法 DB 配置回退到默认库 0。
		db = 0
	}

	// 统一配置连接、读写超时和连接池大小。
	return redis.NewClient(&redis.Options{
		Addr:         addr,
		Password:     password,
		DB:           db,
		DialTimeout:  3 * time.Second,
		ReadTimeout:  2 * time.Second,
		WriteTimeout: 2 * time.Second,
		PoolSize:     20,
	})
}

func getenv(k, fallback string) string {
	// 优先使用环境变量，未配置时使用默认值。
	if v, ok := os.LookupEnv(k); ok {
		return v
	}
	return fallback
}
