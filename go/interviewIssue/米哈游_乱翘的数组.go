package interviewIssue

import (
	"bufio"
	"fmt"
	"os"
)

// [0, 1, 4, 2, 3, 2, 1]

func DisorderedArray() {
	reader, writer := bufio.NewReaderSize(os.Stdin, 1<<20), bufio.NewWriterSize(os.Stdout, 1<<20)
	defer writer.Flush()

	var n int
	fmt.Fscan(reader, &n)
	// dp[i] 表示以 A[i] 结尾的最长乱翘数组的长度
	A, dp := make([]int, n+1), make([]int, n+1)
	// lastLegalLessIndexes, lastLegalGreaterIndexes := make([]int, n+1), make([]int, n+1)
	// flags[i] = -1 表示 dp[i] 是倒数第二小于末尾，flags[i] = 1 表示 dp[i] 是倒数第二大于末尾
	flags := make([]int, n+1)
	for i := 1; i <= n; i++ {
		fmt.Fscan(reader, &A[i])
	}
	dp[1], dp[2] = 1, 2
	if A[2] < A[1] {
		// lastLegalLessIndexes[2] = 1
		flags[2] = 1
	} else if A[2] > A[1] {
		// lastLegalGreaterIndexes[2] = 1
		flags[2] = -1
	}
	// if A[3] < A[2] {
	// 	lastLegalLessIndexes[3] = 2
	// } else if A[3] > A[2] {
	// 	lastLegalGreaterIndexes[3] = 2
	// }

	// 状态更新
	// for i := 3; i < n; i++ {
	// 	// 状态转移：dp[i] = max(上一个比 i 小的同时比该数前一个数也小的数的 dp 值, 上一个比 i 大的同时比该数的前一个数也大的数的 dp 值) 加 1
	// 	var lastLegalLessIndex, lastLegalGreaterIndex int
	// 	for j := i - 1; j >= 2; j-- {
	// 		if A[j] < A[i] {
	// 			if flags[j] ==
	// 		}
	// 	}
	// 	for j := i - 1; j >= 2; j-- {
	// 		if A[j] > A[i] {
	// 		}
	// 	}

	// 	dp[i] = max(dp[lastLegalLessIndex], dp[lastLegalGreaterIndex]) + 1
	// }

	fmt.Fprintln(writer, dp[n])
}

// 正确思路：摆动序列的动态规划
// Key Insight: 摆动序列的“交替”性质决定了每个元素的状态仅由前一个元素决定（上升或下降）。
// 摆动序列的核心是交替上升和下降，因此我们可以维护两个状态：

// up[i]：以A[i]结尾，且最后一个差为上升的最长摆动序列长度。
// down[i]：以A[i]结尾，且最后一个差为下降的最长摆动序列长度。
// 状态转移规则：

// 若 A[i] > A[i-1]（当前上升）：up[i] = down[i-1] + 1（前一个必须是下降），down[i] = down[i-1]（下降状态不变）。
// 若 A[i] < A[i-1]（当前下降）：down[i] = up[i-1] + 1（前一个必须是上升），up[i] = up[i-1]（上升状态不变）。
// 若 A[i] == A[i-1]（相等）：up[i] = up[i-1]，down[i] = down[i-1]（状态不变）。
// 最终，最长摆动序列长度为 max(up[n], down[n])，最少删除个数为 n - max(up[n], down[n])。
func DisorderedArrayChatGLM() {
	reader := bufio.NewReaderSize(os.Stdin, 1<<20)
	writer := bufio.NewWriterSize(os.Stdout, 1<<20)
	defer writer.Flush()

	var n int
	fmt.Fscan(reader, &n)
	A := make([]int, n+1)
	for i := 1; i <= n; i++ {
		fmt.Fscan(reader, &A[i])
	}

	// 特殊处理n=1的情况（题目中n≥3，但代码需兼容）
	if n == 1 {
		fmt.Fprintln(writer, 0)
		return
	}

	// up[i]：以A[i]结尾，最后一个差为上升的最长摆动序列长度
	// down[i]：以A[i]结尾，最后一个差为下降的最长摆动序列长度
	up := make([]int, n+1)
	down := make([]int, n+1)
	up[1] = 1
	down[1] = 1

	for i := 2; i <= n; i++ {
		if A[i] > A[i-1] {
			up[i] = down[i-1] + 1
			down[i] = down[i-1]
		} else if A[i] < A[i-1] {
			down[i] = up[i-1] + 1
			up[i] = up[i-1]
		} else {
			up[i] = up[i-1]
			down[i] = down[i-1]
		}
	}

	maxLen := max(up[n], down[n])
	fmt.Fprintln(writer, n-maxLen)
}
