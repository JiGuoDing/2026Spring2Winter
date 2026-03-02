package src

import (
	"bufio"
	"fmt"
	"os"
)

func P1028() {
	reader := bufio.NewReaderSize(os.Stdin, 1<<20)
	var n int
	fmt.Fscan(reader, &n)

	// dp[i] 表示从 i 开始到结束，能产生的不同序列的个数
	dp := make([]int, n+1)
	dp[0] = 1
	dp[1] = 1

	for i := 2; i <= n; i++ {
		// 状态转移方程
		for j := 0; j <= i/2; j++ {
			dp[i] += dp[j]
		}
	}

	fmt.Println(dp[n])
}
