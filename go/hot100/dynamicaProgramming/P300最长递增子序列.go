package dynamicProgramming

func lengthOfLIS(nums []int) int {
	// 处理边界情况
	if len(nums) == 1 {
		return 1
	}
	// * dp[i] 表示以 nums[i] 结尾的的最长递增子序列，不然不好进行状态转移
	dp := make([]int, len(nums)+1)
	for i := range dp {
		dp[i] = 1
	}

	maxLen := 1

	// 转移方程
	// dp[i] = max(dp[i], dp[j] + 1)
	// 对于每一个位置 i，我们需要检查它之前的所有位置 j，如果 nums[i] 大于 nums[j]，那么我们就可以将 nums[i] 加入到以 nums[j] 结尾的子序列中，得到一个更长的子序列
	// 到以 nums[i] 结尾的子序列中，我们取其中的最长的子序列长度，作为 dp[i] 的值。
	for i := range dp[:len(nums)] {
		for j := 0; j < i; j++ {
			if nums[i] > nums[j] {
				// 状态转移：尝试接在 j 后面，看是否更长
				dp[i] = max(dp[i], dp[j]+1)
				maxLen = max(maxLen, dp[i])
			}
		}
	}

	return maxLen
}
