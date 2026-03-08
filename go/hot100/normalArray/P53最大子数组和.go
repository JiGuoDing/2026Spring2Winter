package normalarray

func maxSubArray(nums []int) int {
	maxSubSum, currentSum := nums[0], nums[0]

	// 从索引 1 开始
	for _, num := range nums[1:] {
		// 核心抉择：是加入前面的连续子数组，还是从自己开始另起新数组？
		if currentSum > 0 {
			// 前面是正资产，加入前面的子数组
			currentSum += num
		} else {
			// 前面是负资产，从自己开始
			currentSum = num
		}
		maxSubSum = max(maxSubSum, currentSum)
	}

	return maxSubSum
}
