package main

import (
	"context"
	"errors"
	"fmt"
	"os"
	"strconv"
	"time"

	"github.com/redis/go-redis/v9"
)

var unlockScript = redis.NewScript(`
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('DEL', KEYS[1])
else
  return 0
end
`)

func main() {
	// 先演示分布式锁，再演示 Cache Aside。
	ctx := context.Background()
	rdb := newClient()
	defer rdb.Close()

	// 锁相关流程。
	if err := demoLock(ctx, rdb); err != nil {
		panic(err)
	}
	// 缓存读写流程。
	if err := demoCacheAside(ctx, rdb); err != nil {
		panic(err)
	}
}

func demoLock(ctx context.Context, rdb *redis.Client) error {
	lockKey := "lock:order:9001"
	requestID := "req-001"

	// SetNX + 过期时间：加锁基础模式。
	ok, err := rdb.SetNX(ctx, lockKey, requestID, 20*time.Second).Result()
	if err != nil {
		return err
	}
	if !ok {
		// 加锁失败一般表示已有其他请求持有锁。
		return errors.New("failed to acquire lock")
	}
	fmt.Println("lock acquired")

	// 释放锁时校验 requestID，防止误删其他请求的锁。
	_, err = unlockScript.Run(ctx, rdb, []string{lockKey}, requestID).Result()
	if err != nil {
		return err
	}
	fmt.Println("lock released")
	return nil
}

func demoCacheAside(ctx context.Context, rdb *redis.Client) error {
	cacheKey := "product:1001:detail"
	// 先查缓存，命中就直接返回。
	v, err := rdb.Get(ctx, cacheKey).Result()
	if err == nil {
		fmt.Println("cache hit:", v)
		return nil
	}
	// 非空值错误直接返回，避免吞掉真实故障。
	if err != redis.Nil {
		return err
	}

	// miss 后模拟查库并回填缓存。
	dbValue := `{"id":1001,"name":"keyboard","price":399}`
	if err = rdb.Set(ctx, cacheKey, dbValue, 3*time.Minute).Err(); err != nil {
		return err
	}
	fmt.Println("cache miss -> rebuild from db")
	return nil
}

func newClient() *redis.Client {
	// 连接参数从环境变量注入。
	addr := getenv("REDIS_ADDR", "127.0.0.1:6379")
	password := getenv("REDIS_PASSWORD", "")
	db, err := strconv.Atoi(getenv("REDIS_DB", "0"))
	if err != nil {
		db = 0
	}
	return redis.NewClient(&redis.Options{Addr: addr, Password: password, DB: db})
}

func getenv(k, fallback string) string {
	// 返回配置值，不存在时回退到默认值。
	if v, ok := os.LookupEnv(k); ok {
		return v
	}
	return fallback
}
