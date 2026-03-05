package src

import (
	"bufio"
	"fmt"
	"os"
)

func BigIntAdd(bigIntA, bigIntB []int) []int {
	maxLen := max(len(bigIntA), len(bigIntB))
	res := make([]int, 0, maxLen+1)
	carry := 0

	for i := range maxLen {
		var a, b int
		if i < len(bigIntA) {
			a = bigIntA[i]
		}
		if i < len(bigIntB) {
			b = bigIntB[i]
		}
		temp := a + b + carry
		res = append(res, temp%10)
		carry = temp / 10
	}

	if carry > 0 {
		res = append(res, carry)
	}

	return res

}

func P2437() {
	var m, n int
	reader := bufio.NewReaderSize(os.Stdin, 1<<20)
	writer := bufio.NewWriterSize(os.Stdout, 1<<20)
	fmt.Fscan(reader, &m, &n)
	defer writer.Flush()

	// 转移方程：dp[i] = dp[i-1] + dp[i-2]
	dp := make([][]int, n+1)
	// dp[1] = []int{1}
	// dp[2] = []int{1}
	dp[m] = []int{1}
	dp[m+1] = []int{1}

	for i := m + 2; i <= n; i++ {
		dp[i] = BigIntAdd(dp[i-1], dp[i-2])
	}

	for i := len(dp[n]) - 1; i >= 0; i-- {
		fmt.Fprint(writer, dp[n][i])
	}
}
