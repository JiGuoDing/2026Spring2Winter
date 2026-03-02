package src

import (
	"bufio"
	"fmt"
	"os"
)

func P1044() {
	var n int
	reader := bufio.NewReaderSize(os.Stdin, 1<<20)
	fmt.Fscan(reader, &n)

	// dp[i][j] 表示从当前状态 (还有 i 个元素未入栈，而栈中还有 j 个元素) 走到终止状态能生成的不同序列的个数
	dp := make([][]int, n+2)
	for i := range dp {
		dp[i] = make([]int, n+2)
	}

	// i 表示当前还未入栈的元素个数
	for i := range n + 1 {
		// j 表示当前栈中元素个数
		for j := range n + 1 {
			// 在状态 (i, j)，下一步只有两种操作，但受合法性约束
			if i == 0 {
				// 只能是出栈操作
				dp[i][j] = 1
			} else if j == 0 {
				// 只能是入栈操作，即与入栈一个元素后的状态相同
				dp[i][j] = dp[i-1][j+1]
			} else {
				// 既能入栈，也能出栈
				// 状态转移方程为
				dp[i][j] = dp[i-1][j+1] + dp[i][j-1]
			}
		}
	}

	fmt.Println(dp[n][0])
}
