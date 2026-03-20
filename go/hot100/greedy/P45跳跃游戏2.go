package greedy

func jump(nums []int) int {
	// 处理边界情况
	if len(nums) <= 1 {
		return 0
	}

	// fartherest 表示当前一跳和后续一跳最远能到达的索引，stepCnt 表示已经走过的步数，currentEnd 表示当前一跳能跳到的最远索引
	fartherest, stepCnt, currentEnd := 0, 0, 0

	for i := 0; i < len(nums)-1; i++ {
		fartherest = max(fartherest, i+nums[i])

		// 到了当前跳跃步骤必须跳的边界，必须进行一次跳跃
		if i == currentEnd {
			stepCnt++
			currentEnd = fartherest

			if currentEnd >= len(nums)-1 {
				break
			}
		}
	}
	return stepCnt
}
