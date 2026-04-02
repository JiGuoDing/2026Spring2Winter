package redis

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/redis/go-redis/v9"
)

// 定义一个全局的 ctx，用于控制 Redis 操作的超时和取消
var ctx = context.Background()

func ConnectRedis() {
	// 1. 创建 Redis 客户端实例
	rdb := redis.NewClient(&redis.Options{
		Addr:         "210.28.132.19:6397", // Redis 服务器地址，格式：host:port
		Password:     "",                   // Redis 密码，如果没有设置密码则为空
		DB:           0,                    // Redis 数据库编号，默认是 0
		DialTimeout:  5 * time.Second,      // 连接超时时间
		ReadTimeout:  3 * time.Second,      // 读取超时时间
		WriteTimeout: 3 * time.Second,      // 写入超时时间
		PoolSize:     10,                   // 连接池大小
	})

	// 2. 测试连接是否成功 (Ping 命令)
	pong, err := rdb.Ping(ctx).Result()
	if err != nil {
		log.Fatalf("Failed to connect to Redis: %v", err)
	}
	fmt.Printf("Successfully connected to Redis: %s\n\n", pong)

	// 3. 示例：写入数据 (Set 命令)
	// 参数说明：ctx, key, value, 过期时间 (0 表示永不过期)
	err = rdb.Set(ctx, "mykey", "Hello, Redis with Go!", 10*time.Minute).Err()
	if err != nil {
		log.Fatalf("Failed to set key: %v", err)
	}
	fmt.Println("Successfully set key: 'mykey'")

	// 4. 示例：读取数据 (Get 命令)
	val, err := rdb.Get(ctx, "mykey").Result()
	if err != nil {
		if err == redis.Nil {
			fmt.Println("Key does not exist")
		} else {
			log.Fatalf("Failed to get key: %v", err)
		}
	} else {
		fmt.Printf("The value of 'mykey' is: %s\n\n", val)
	}

	// 5. 示例：删除数据 (Del 命令)
	deleted, err := rdb.Del(ctx, "mykey").Result()
	if err != nil {
		log.Fatalf("Failed to delete key: %v", err)
	}
	fmt.Printf("Successfully deleted %d key(s)\n", deleted)
}
