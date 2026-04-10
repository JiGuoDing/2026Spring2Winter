package stack

// 该方法的时间复杂度为 O(n^2) 会超时
func dailyTemperatures(temperatures []int) []int {
	answer := make([]int, len(temperatures))
	for idx, temperature := range temperatures {
		if idx == 0 {
			continue
		}
		for subIdx, formerTemperature := range temperatures[:idx] {
			if formerTemperature < temperature {
				if answer[subIdx] == 0 {
					answer[subIdx] = idx - subIdx
				}
			}
		}
	}
	return answer
}

func dailyTemperaturesImproved(temperatures []int) []int {
	answer := make([]int, len(temperatures))
	// 单调递减栈，存储索引
	stack := make([]int, 0)

	for idx, temperature := range temperatures {
		for len(stack) > 0 && temperatures[stack[len(stack)-1]] < temperature {
			// 当前温度比栈顶高，找到栈顶的答案
			// 记录栈顶索引
			prevIdx := stack[len(stack)-1]
			// 弹出栈顶
			stack = stack[:len(stack)-1]
			// 计算等待天数
			answer[prevIdx] = idx - prevIdx
		}
		// 当前索引入栈
		stack = append(stack, idx)
	}

	return answer
}
