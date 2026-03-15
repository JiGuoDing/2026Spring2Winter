// package声明为main，是可执行程序入口
package main

import (
	"log/slog"
	"luogu/go/hot100/binarySearch"
)

func main() {
	nums := []int{4, 5, 6, 7, 0, 1, 2}
	slog.Info("result: ", "result", binarySearch.Search(nums, 0))
}
