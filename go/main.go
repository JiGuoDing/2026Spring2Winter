// package声明为main，是可执行程序入口
package main

import (
	"luogu/go/redis"
)

func main() {
	redis.ConnectRedis()
}
