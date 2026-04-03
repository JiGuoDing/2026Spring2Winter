package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"strconv"
	"time"

	"github.com/redis/go-redis/v9"
)

type User struct {
	ID    int    `json:"id"`
	Name  string `json:"name"`
	Level int    `json:"level"`
}

func main() {
	// 这里使用 Background 作为演示场景上下文。
	ctx := context.Background()
	// 创建客户端并复用连接池。
	rdb := newClient()
	defer rdb.Close()

	// 演示 String 类型常见操作。
	if err := demoString(ctx, rdb); err != nil {
		panic(err)
	}
	// 演示 Hash 类型常见操作。
	if err := demoHash(ctx, rdb); err != nil {
		panic(err)
	}
}

func demoString(ctx context.Context, rdb *redis.Client) error {
	// 模拟业务对象并序列化后存入 String。
	u := User{ID: 1001, Name: "alice", Level: 3}
	b, _ := json.Marshal(u)

	key := "user:json:1001"
	// Set + 过期时间是最常见的缓存写入模式。
	if err := rdb.Set(ctx, key, string(b), 2*time.Minute).Err(); err != nil {
		return err
	}

	// IncrBy 演示原子计数器，常用于登录次数、访问量。
	if err := rdb.IncrBy(ctx, "counter:login", 1).Err(); err != nil {
		return err
	}

	// 读取 String 内容，验证写入结果。
	val, err := rdb.Get(ctx, key).Result()
	if err != nil {
		return err
	}
	fmt.Println("string value:", val)
	return nil
}

func demoHash(ctx context.Context, rdb *redis.Client) error {
	key := "user:hash:1001"
	// HSet 一次写入多个字段，适合对象局部更新场景。
	if err := rdb.HSet(ctx, key,
		"name", "alice",
		"city", "shanghai",
		"age", 28,
	).Err(); err != nil {
		return err
	}

	// HIncrBy 可对单个字段做原子自增。
	if err := rdb.HIncrBy(ctx, key, "login_count", 1).Err(); err != nil {
		return err
	}

	// HGetAll 读取完整对象字段。
	m, err := rdb.HGetAll(ctx, key).Result()
	if err != nil {
		return err
	}
	fmt.Println("hash fields:", m)
	return nil
}

func newClient() *redis.Client {
	// 连接参数支持环境变量覆盖，便于本地和线上切换。
	addr := getenv("REDIS_ADDR", "127.0.0.1:6379")
	password := getenv("REDIS_PASSWORD", "")
	db, err := strconv.Atoi(getenv("REDIS_DB", "0"))
	if err != nil {
		db = 0
	}
	return redis.NewClient(&redis.Options{Addr: addr, Password: password, DB: db})
}

func getenv(k, fallback string) string {
	// 读取环境变量并提供默认值兜底。
	if v, ok := os.LookupEnv(k); ok {
		return v
	}
	return fallback
}
