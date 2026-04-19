package interviewIssue

import (
	"bufio"
	"fmt"
	"os"
)

// 主要思路就是用到了栈

func solveCase(a []int) int {
	// 单调递增栈
	stack := []int{}
	ans := 0

	for _, x := range a {
		// 弹出所有比当前值大的元素
		for len(stack) > 0 && stack[len(stack)-1] > x {
			// 若差值为 1，则形成合法数对
			if stack[len(stack)-1] == x+1 {
				ans++
			}
			stack = stack[:len(stack)-1] // pop
		}

		// 弹栈结束后，若栈顶恰好是 x - 1，也能形成合法数对
		if len(stack) > 0 && stack[len(stack)-1] == x-1 {
			ans++
		}

		// 维护严格递增栈
		if len(stack) == 0 || stack[len(stack)-1] < x {
			stack = append(stack, x)
		}
		// 若栈顶等于当前值，则不需要入栈
	}

	return ans
}

func NumberInterval() {
	reader := bufio.NewReader(os.Stdin)
	var t int
	fmt.Fscan(reader, &t)

	results := make([]string, 0, t)

	for i := 0; i < t; i++ {
		var n int
		fmt.Fscan(reader, &n)
		a := make([]int, n)
		for j := 0; j < n; j++ {
			fmt.Fscan(reader, &a[j])
		}
		results = append(results, fmt.Sprint(solveCase(a)))
	}

	for _, res := range results {
		fmt.Println(res)
	}
}
