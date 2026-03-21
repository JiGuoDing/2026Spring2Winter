package dynamicProgramming

func rob(nums []int) int {
	dp := make([]int, len(nums))
	// 处理边界情况
	if len(nums) == 1 {
		return nums[0]
	}
	if len(nums) == 2 {
		return max(nums[0], nums[1])
	}

	// 要正确初始化
	dp[0], dp[1] = nums[0], max(nums[0], nums[1])

	for i := 2; i < len(nums); i++ {
		// 状态转移方程
		dp[i] = max(dp[i-2]+nums[i], dp[i-1])
	}
	return dp[len(dp)-1]
}
