package dynamicProgramming

// 求一个 int slice 的所有元素和
func sliceSum(nums []int) int {
	sum := 0
	for _, num := range nums {
		sum += num
	}
	return sum
}

// 回溯法会超时
func canPartitionBackTrack(nums []int) bool {
	// originalSum := slices.Sum(nums)
	originalSum, currentSum := sliceSum(nums), 0

	// 如果原切片的总和不是偶数，直接返回 false
	if originalSum%2 != 0 {
		return false
	}

	var backtrap func(position int) bool
	backtrap = func(position int) bool {
		if currentSum == originalSum/2 {
			return true
		} else if currentSum > originalSum/2 {
			return false
		}

		for index, num := range nums[position:] {
			currentSum += num
			if backtrap(position + index + 1) {
				return true
			}
			currentSum -= num
		}

		return false
	}

	return backtrap(0)
}

func canPartition(nums []int) bool {
	// originalSum := slices.Sum(nums)
	originalSum := sliceSum(nums)

	// 如果原切片的总和不是偶数，直接返回 false
	if originalSum%2 != 0 {
		return false
	}
	targetSum := originalSum / 2

	// dp[i] 表示是否可以从当前已经遍历过的数字中选出若干个，使它们的和恰好为 i
	dp := make([]bool, targetSum+1)
	dp[0] = true

	// 状态转移：判断 dp[i - num] 是否为真，如果是的话，dp[i] 就为真
	for _, num := range nums {
		// 【关键点】：必须从后向前遍历 (target -> num)
		// 原因：防止同一个数字在同一轮中被重复使用多次。
		// 如果从前向后遍历，dp[i-num] 可能已经是被当前 num 更新过的值，导致错误。
		for i := targetSum; i >= num; i-- {
			if dp[i-num] {
				dp[i] = true
			}
		}
		if dp[targetSum] {
			return true
		}
	}

	return false
}
