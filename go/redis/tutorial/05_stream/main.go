package main

import (
	"context"
	"fmt"
	"os"
	"strconv"
	"strings"

	"github.com/redis/go-redis/v9"
)

func main() {
	// Stream 演示：生产消息、消费组读取、ACK 确认。
	ctx := context.Background()
	rdb := newClient()
	defer rdb.Close()

	if err := demoStream(ctx, rdb); err != nil {
		panic(err)
	}
}

func demoStream(ctx context.Context, rdb *redis.Client) error {
	stream := "stream:order"
	group := "group_order"
	consumer := "consumer_1"

	// 清理旧流，确保示例每次可重复执行。
	_ = rdb.Del(ctx, stream).Err()
	// 创建消费组；已存在时忽略 BUSYGROUP 错误。
	if err := rdb.XGroupCreateMkStream(ctx, stream, group, "0").Err(); err != nil {
		if !strings.Contains(err.Error(), "BUSYGROUP") {
			return err
		}
	}

	// 生产一条订单事件。
	id, err := rdb.XAdd(ctx, &redis.XAddArgs{
		Stream: stream,
		Values: map[string]any{"order_id": 9001, "status": "created"},
	}).Result()
	if err != nil {
		return err
	}
	fmt.Println("produced msg id:", id)

	// 使用消费组读取新消息，> 表示仅拉取未投递过的消息。
	res, err := rdb.XReadGroup(ctx, &redis.XReadGroupArgs{
		Group:    group,
		Consumer: consumer,
		Streams:  []string{stream, ">"},
		Count:    10,
		// Block=0 表示阻塞等待直到有消息。
		Block: 0,
	}).Result()
	if err != nil {
		return err
	}
	fmt.Println("consumed:", res)

	// 成功处理后发送 ACK，从待确认列表移除该消息。
	if len(res) > 0 && len(res[0].Messages) > 0 {
		msgID := res[0].Messages[0].ID
		if err = rdb.XAck(ctx, stream, group, msgID).Err(); err != nil {
			return err
		}
		fmt.Println("acked:", msgID)
	}

	return nil
}

func newClient() *redis.Client {
	// 读取环境变量作为连接配置。
	addr := getenv("REDIS_ADDR", "127.0.0.1:6379")
	password := getenv("REDIS_PASSWORD", "")
	db, err := strconv.Atoi(getenv("REDIS_DB", "0"))
	if err != nil {
		db = 0
	}
	return redis.NewClient(&redis.Options{Addr: addr, Password: password, DB: db})
}

func getenv(k, fallback string) string {
	// 环境变量优先，默认值兜底。
	if v, ok := os.LookupEnv(k); ok {
		return v
	}
	return fallback
}
