package interviewIssue

import (
	"bufio"
	"fmt"
	"os"
)

func StabilityAnalysis() {
	reader := bufio.NewReaderSize(os.Stdin, 1<<20)
	writer := bufio.NewWriterSize(os.Stdout, 1<<20)
	defer writer.Flush()

	var N int
	fmt.Fscan(reader, &N)
	exponents := make([]int, N)
	for i := 0; i < N; i++ {
		fmt.Fscan(reader, &exponents[i])
	}

	maxLength := 0
	results := make([][]int, 0)

	// 使用切片模拟双端单调队列，里面存的是【索引】
	minQ := make([]int, 0) // 单调递增队列，队首永远是当前窗口的最小值索引
	maxQ := make([]int, 0) // 单调递减队列，队首永远是当前窗口的最大值索引

	left := 0
	for right := 0; right < N; right++ {
		val := exponents[right]

		// 条件1：如果当前元素不在 [18, 24] 内，它绝对不能作为任何合法区间的一部分
		if val < 18 || val > 24 {
			// 直接跳过这个元素，将左边界移到下一个位置，并清空队列
			left = right + 1
			minQ = minQ[:0]
			maxQ = maxQ[:0]
			continue
		}

		// 维护单调递增队列（求窗口最小值）
		for len(minQ) > 0 && exponents[minQ[len(minQ)-1]] >= val {
			minQ = minQ[:len(minQ)-1] // 弹出队尾大于等于当前值的元素
		}
		minQ = append(minQ, right)

		// 维护单调递减队列（求窗口最大值）
		for len(maxQ) > 0 && exponents[maxQ[len(maxQ)-1]] <= val {
			maxQ = maxQ[:len(maxQ)-1] // 弹出队尾小于等于当前值的元素
		}
		maxQ = append(maxQ, right)

		// 条件2：极差不能超过 4。如果不满足，收缩左边界 left
		for exponents[maxQ[0]]-exponents[minQ[0]] > 4 {
			// 如果要移出的左边界刚好是队列的队首，则将队首弹出
			if minQ[0] == left {
				minQ = minQ[1:]
			}
			if maxQ[0] == left {
				maxQ = maxQ[1:]
			}
			left++ // 左边界向右收缩
		}

		// 此时 [left, right] 一定是一个满足所有条件的合法区间
		currLength := right - left + 1
		if currLength > maxLength {
			maxLength = currLength
			results = append(results[:0], []int{left, right}) // 发现更长区间，清空旧结果并记录
		} else if currLength == maxLength && maxLength > 0 {
			results = append(results, []int{left, right}) // 长度一样，追加记录
		}
	}

	// 输出结果
	for _, result := range results {
		fmt.Fprintf(writer, "%d %d\n", result[0], result[1])
	}
}
