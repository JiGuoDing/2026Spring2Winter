package src

import (
	"bufio"
	"fmt"
	"os"
)

func P1164() {
	reader := bufio.NewReaderSize(os.Stdin, 1<<20)
	writer := bufio.NewWriterSize(os.Stdout, 1<<20)
	defer writer.Flush()

	var n, m int
	fmt.Fscan(reader, &n, &m)
	dishPrice := make([]int, n+1)
	for i := 1; i <= n; i++ {
		fmt.Fscan(reader, &dishPrice[i])
	}

	// dp[i][j] 表示用前 i 道菜，花光 j 元的办法总数
	dp := make([][]int, n+1)
	for i := range dp {
		dp[i] = make([]int, m+1)
	}

	// 将所有 dp[i][0] 置为 1
	for i := 0; i <= n; i++ {
		dp[i][0] = 1
	}

	for i := 1; i <= n; i++ {
		for j := 1; j <= m; j++ {
			// 转移方程，考虑是否买第 i 道菜
			// 1. 不买第 i 道菜，方法数与用前 i-1 道菜，花光 j 元相同，即 dp[i-1][j] 相同
			dp[i][j] += dp[i-1][j]
			// 2. 买第 i 道菜，方法数为对于前 i-1 道菜，花光 j-dishPrice[i] 的方法数，即 dp[i-1][j-dishPrice[i]] 相同
			if j >= dishPrice[i] {
				dp[i][j] += dp[i-1][j-dishPrice[i]]
			}
		}
	}

	// for i := 0; i <= n; i++ {
	// 	for j := 0; j <= m; j++ {
	// 		fmt.Fprintf(writer, "%d ", dp[i][j])
	// 	}
	// 	fmt.Fprintln(writer, "")
	// }

	// 输出结果
	fmt.Fprintln(writer, dp[n][m])

}

func P1164_improved() {
	reader := bufio.NewReaderSize(os.Stdin, 1<<20)
	writer := bufio.NewWriterSize(os.Stdout, 1<<20)
	defer writer.Flush()

	var n, m int
	fmt.Fscan(reader, &n, &m)
	dishPrice := make([]int, n+1)
	for i := 1; i <= n; i++ {
		fmt.Fscan(reader, &dishPrice[i])
	}

	dp := make([]int, m+1)
	dp[0] = 1

	for i := 1; i <= n; i++ {
		for j := m; j >= dishPrice[i]; j-- {
			// 状态转移：总花费 j 元的方案数 += 花费 (j - 第 i 道菜的钱) 的方案数
			// 对于前 i 道菜，总花费 j 元的方案数 = 对于前 i - 1 道菜，总花费 j 元的方案数 + 对于前 i - 1 道菜，花费 j - 第 i 道菜钱的方案数
			dp[j] += dp[j-dishPrice[i]]
		}
	}

	fmt.Fprintln(writer, dp[m])
}
