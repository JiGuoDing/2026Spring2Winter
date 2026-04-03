package main

import (
	"context"
	"fmt"
	"os"
	"strconv"

	"github.com/redis/go-redis/v9"
)

func main() {
	// 示例里连续演示三种数据结构。
	ctx := context.Background()
	rdb := newClient()
	defer rdb.Close()

	// List: 队列类场景。
	if err := demoList(ctx, rdb); err != nil {
		panic(err)
	}
	// Set: 去重与集合运算。
	if err := demoSet(ctx, rdb); err != nil {
		panic(err)
	}
	// ZSet: 排行与有序检索。
	if err := demoZSet(ctx, rdb); err != nil {
		panic(err)
	}
}

func demoList(ctx context.Context, rdb *redis.Client) error {
	queue := "q:email"
	// 先清空旧数据，确保结果可重复。
	if err := rdb.Del(ctx, queue).Err(); err != nil {
		return err
	}
	// 头插写入多个任务。
	if err := rdb.LPush(ctx, queue, "job-1", "job-2", "job-3").Err(); err != nil {
		return err
	}
	// 读取完整列表，观察当前队列顺序。
	jobs, err := rdb.LRange(ctx, queue, 0, -1).Result()
	if err != nil {
		return err
	}
	fmt.Println("list jobs:", jobs)
	return nil
}

func demoSet(ctx context.Context, rdb *redis.Client) error {
	a := "tag:article:1"
	b := "tag:article:2"
	// 清理旧集合，避免测试污染。
	if err := rdb.Del(ctx, a, b).Err(); err != nil {
		return err
	}
	// 写入两个文章的标签集合。
	if err := rdb.SAdd(ctx, a, "redis", "go", "cache").Err(); err != nil {
		return err
	}
	if err := rdb.SAdd(ctx, b, "redis", "interview").Err(); err != nil {
		return err
	}
	// 计算交集，得到共同标签。
	inter, err := rdb.SInter(ctx, a, b).Result()
	if err != nil {
		return err
	}
	fmt.Println("set inter:", inter)
	return nil
}

func demoZSet(ctx context.Context, rdb *redis.Client) error {
	key := "rank:game"
	// 重置排行榜数据。
	if err := rdb.Del(ctx, key).Err(); err != nil {
		return err
	}
	// score 越高排名越靠前。
	if err := rdb.ZAdd(ctx, key,
		redis.Z{Score: 1200, Member: "u1"},
		redis.Z{Score: 980, Member: "u2"},
		redis.Z{Score: 1350, Member: "u3"},
	).Err(); err != nil {
		return err
	}
	// 按分数倒序取前 3 名。
	res, err := rdb.ZRevRangeWithScores(ctx, key, 0, 2).Result()
	if err != nil {
		return err
	}
	fmt.Println("zset top:", res)
	return nil
}

func newClient() *redis.Client {
	// 统一读取连接参数。
	addr := getenv("REDIS_ADDR", "127.0.0.1:6379")
	password := getenv("REDIS_PASSWORD", "")
	db, err := strconv.Atoi(getenv("REDIS_DB", "0"))
	if err != nil {
		db = 0
	}
	return redis.NewClient(&redis.Options{Addr: addr, Password: password, DB: db})
}

func getenv(k, fallback string) string {
	// 从环境变量读取配置，不存在时使用默认值。
	if v, ok := os.LookupEnv(k); ok {
		return v
	}
	return fallback
}
