package dynamicProgramming

func maxProduct(nums []int) int {
	if len(nums) == 0 {
		return 0
	}

	// maxP 表示以当前数字结尾的最大乘积
	// minP 表示以当前数字结尾的最小乘积
	// ans 表示全局最大乘积
	maxP, minP, ans := nums[0], nums[0], nums[0]

	// 状态转移：在每个位置 i，有三种选择
	// 1. 只取 nums[i] 本身 (重新开始一段子数组)
	// 2. maxP * nums[i]
	// 3. minP * nums[i]
	for i := 1; i < len(nums); i++ {
		// 如果 nums[i] 为负数，则 maxP 和 minP 角色会互换
		prevMax := maxP

		maxP = max(nums[i], prevMax*nums[i], minP*nums[i])
		minP = min(nums[i], prevMax*nums[i], minP*nums[i])

		ans = max(maxP, ans)
	}

	return ans
}
