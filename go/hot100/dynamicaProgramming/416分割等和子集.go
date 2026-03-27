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

// ============================================================================
// 【更好理解的版本】- 详细注释版
// ============================================================================

// canPartitionV2 更容易理解的动态规划版本
// 问题本质：能否将数组分割成两个子集，使得两个子集的元素和相等
// 等价于：能否从数组中选出一些元素，使它们的和等于总和的一半（背包问题）
func canPartitionV2(nums []int) bool {
	// Step 1: 计算总和
	totalSum := 0
	for _, num := range nums {
		totalSum += num
	}

	// 【剪枝 1】如果总和是奇数，不可能分成两个相等的子集
	if totalSum%2 != 0 {
		return false
	}

	target := totalSum / 2 // 目标和（背包容量）

	// Step 2: 定义 dp 数组
	// dp[i] 的含义：能否凑出和为 i
	// dp[i] = true  表示可以凑出和为 i
	// dp[i] = false 表示无法凑出和为 i
	dp := make([]bool, target+1)

	// Step 3: 初始化 dp 数组
	// dp[0] = true，因为不选任何数字时，和为 0
	dp[0] = true

	// Step 4: 状态转移
	// 遍历每个数字，更新所有可能的和
	for _, num := range nums {
		// 【关键点】必须从后向前遍历！
		// 原因：这是 0-1 背包问题的一维数组优化
		// 每个数字只能用一次，从后向前可以避免重复使用
		//
		// 举例说明为什么要从后向前：
		// 假设 target=5, num=2, 当前 dp=[T,F,T,F,F,F]
		// 如果从前向后：dp[2]=T(用 num), dp[4]=dp[2]=T(又用了一次 num) ❌
		// 如果从后向前：dp[5]=dp[3], dp[4]=dp[2], dp[3]=dp[1], dp[2]=dp[0]=T ✅
		for j := target; j >= num; j-- {
			// 状态转移方程：
			// dp[j] = dp[j] (不选当前数字) || dp[j-num] (选当前数字)
			// 由于是布尔值，只要 dp[j-num] 为 true，dp[j] 就为 true
			if dp[j-num] {
				dp[j] = true
			}
		}

		// 【提前终止优化】如果已经能凑出 target，直接返回
		if dp[target] {
			return true
		}
	}

	// Step 5: 返回结果
	return dp[target]
}

// 【可视化示例】nums = [1, 5, 11, 5]
// totalSum = 22, target = 11
//
// dp 数组变化过程（只展示部分关键位置）：
// 初始：dp[0]=T, 其他=F
//
// 处理 num=1:
// dp[1] = dp[1] || dp[0] = T
// 结果：dp[0]=T, dp[1]=T
//
// 处理 num=5:
// dp[6] = dp[6] || dp[1] = T
// dp[5] = dp[5] || dp[0] = T
// 结果：dp[0]=T, dp[1]=T, dp[5]=T, dp[6]=T
//
// 处理 num=11:
// dp[11] = dp[11] || dp[0] = T  ← 找到了！
// 直接返回 true
//
// 【空间复杂度对比】
// 二维 DP: O(n * target) - 更直观但占用空间大
// 一维 DP: O(target)       - 需要理解从后向前遍历的原因
