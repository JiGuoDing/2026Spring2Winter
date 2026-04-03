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
	// 演示 Pipeline 与事务的差异化使用。
	ctx := context.Background()
	rdb := newClient()
	defer rdb.Close()

	// Pipeline: 重点是减少网络往返。
	if err := demoPipeline(ctx, rdb); err != nil {
		panic(err)
	}
	// Watch + TxPipelined: 重点是并发安全更新。
	if err := demoTx(ctx, rdb); err != nil {
		panic(err)
	}
}

func demoPipeline(ctx context.Context, rdb *redis.Client) error {
	key := "pv:homepage"
	// 批量发送命令，降低 RTT。
	pipe := rdb.Pipeline()
	incr := pipe.IncrBy(ctx, key, 10)
	ttl := pipe.Expire(ctx, key, 10*time.Minute)
	// Exec 统一提交并执行。
	_, err := pipe.Exec(ctx)
	if err != nil {
		return err
	}
	fmt.Println("pipeline incr:", incr.Val(), "expire set:", ttl.Val())
	return nil
}

func demoTx(ctx context.Context, rdb *redis.Client) error {
	key := "stock:item:1001"
	// 初始化库存，便于演示扣减。
	if err := rdb.Set(ctx, key, 5, 0).Err(); err != nil {
		return err
	}

	// Watch 监听 key，若并发修改会触发重试或失败。
	err := rdb.Watch(ctx, func(tx *redis.Tx) error {
		// 在事务函数内先读取最新库存。
		stock, err := tx.Get(ctx, key).Int()
		if err != nil {
			return err
		}
		// 业务校验：库存不足直接返回。
		if stock <= 0 {
			return fmt.Errorf("stock not enough")
		}

		// 在同一事务里执行扣减与计数。
		_, err = tx.TxPipelined(ctx, func(pipe redis.Pipeliner) error {
			pipe.DecrBy(ctx, key, 1)
			pipe.IncrBy(ctx, "order:created", 1)
			return nil
		})
		return err
	}, key)
	if err != nil {
		return err
	}

	// 输出扣减后的库存值。
	v, _ := rdb.Get(ctx, key).Result()
	fmt.Println("left stock:", v)
	return nil
}

func newClient() *redis.Client {
	// 读取连接配置。
	addr := getenv("REDIS_ADDR", "127.0.0.1:6379")
	password := getenv("REDIS_PASSWORD", "")
	db, err := strconv.Atoi(getenv("REDIS_DB", "0"))
	if err != nil {
		db = 0
	}
	return redis.NewClient(&redis.Options{Addr: addr, Password: password, DB: db})
}

func getenv(k, fallback string) string {
	// 优先使用环境变量。
	if v, ok := os.LookupEnv(k); ok {
		return v
	}
	return fallback
}
