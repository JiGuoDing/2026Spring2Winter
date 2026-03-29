package interviewIssue

import (
	"bufio"
	"fmt"
	"os"
	"sort"
	"strconv"
	"strings"
)

// 计算单组测试数据的最小元素和
func calcMinSum(n, a, b, k int, arr []int) int {
	// 原数组总和
	total := 0
	for _, x := range arr {
		total += x
	}

	// 计算每个数执行操作 1 后的收益：ceil(x / 2) = (x + 1) // 2
	gains := make([]int, n)
	for i, x := range arr {
		gains[i] = (x + 1) / 2
	}

	// 贪心：操作 1 给收益最大的 a 个位置
	sort.Sort(sort.Reverse(sort.IntSlice(gains)))

	reduceByOp1 := 0
	for i := 0; i < a; i++ {
		reduceByOp1 += gains[i]
	}

	// 操作 2 每次固定减少 k，直接全部用满 b 次
	reduceByOp2 := b * k

	return total - reduceByOp1 - reduceByOp2
}

func MainMeituan() {
	reader := bufio.NewReader(os.Stdin)
	writer := bufio.NewWriter(os.Stdout)

	// 读取测试用例数量
	tLine, _ := reader.ReadString('\n')
	tLine = strings.TrimSpace(tLine)
	t, _ := strconv.Atoi(tLine)

	ans := []string{}

	for i := 0; i < t; i++ {
		// 读取 n, a, b, k
		line1, _ := reader.ReadString('\n')
		parts := strings.Fields(strings.TrimSpace(line1))
		n, _ := strconv.Atoi(parts[0])
		a, _ := strconv.Atoi(parts[1])
		b, _ := strconv.Atoi(parts[2])
		k, _ := strconv.Atoi(parts[3])

		// 读取数组
		line2, _ := reader.ReadString('\n')
		arrStr := strings.Fields(strings.TrimSpace(line2))
		arr := make([]int, n)
		for j := 0; j < n; j++ {
			arr[j], _ = strconv.Atoi(arrStr[j])
		}

		result := calcMinSum(n, a, b, k, arr)
		ans = append(ans, strconv.Itoa(result))
	}

	fmt.Fprintln(writer, strings.Join(ans, "\n"))
	writer.Flush()
}
