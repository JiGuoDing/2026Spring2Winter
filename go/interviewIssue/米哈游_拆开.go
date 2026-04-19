package interviewIssue

import (
	"bufio"
	"fmt"
	"os"
)

// solveCase 构造一组满足条件的答案，若无解则返回 nil
func solveCase_1(n, k, m, r int) []int {
	remain := n - k*r
	if remain < 0 || remain%m != 0 {
		return nil
	}

	s := remain / m

	var base, start int
	if r == 0 {
		base = k * (k + 1) / 2
		start = 1
	} else {
		base = k * (k - 1) / 2
		start = 0
	}

	// 连最小和都达不到，无解
	if s < base {
		return nil
	}

	// 构造最小合法序列
	ans := make([]int, k)
	for i := 0; i < k; i++ {
		x := start + i
		ans[i] = r + m*x
	}

	// 将多余部分全部加到最后一个数上
	extra := s - base
	ans[k-1] += extra * m

	return ans
}

func TearApartNumber() {
	reader := bufio.NewReader(os.Stdin)
	var t int
	fmt.Fscan(reader, &t)

	var output []string

	for i := 0; i < t; i++ {
		var n, k, m, r int
		fmt.Fscan(reader, &n, &k, &m, &r)

		ans := solveCase_1(n, k, m, r)
		if ans == nil {
			output = append(output, "NO")
		} else {
			output = append(output, "YES")
			// 将整数切片转为字符串
			line := ""
			for j, v := range ans {
				if j > 0 {
					line += " "
				}
				line += fmt.Sprint(v)
			}
			output = append(output, line)
		}
	}

	fmt.Print(joinStrings(output))
}

// 辅助函数：用换行符连接字符串切片
func joinStrings(strs []string) string {
	if len(strs) == 0 {
		return ""
	}
	result := strs[0]
	for i := 1; i < len(strs); i++ {
		result += "\n" + strs[i]
	}
	return result
}
