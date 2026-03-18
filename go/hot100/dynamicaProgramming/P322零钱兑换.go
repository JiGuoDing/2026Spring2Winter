package dynamicaProgramming

// 外层遍历总金额数，内层遍历硬币
func coinChange(coins []int, amount int) int {
	if amount == 0 {
		return 0
	}

	// dp[i] 表示总金额为 i 时，可以凑成总金额所需的最少的硬币个数
	dp := make([]int, amount+1)
	// 初始化
	for i := 1; i <= amount; i++ {
		// 面值最小为 1，因此合法的组合数一定会小于等于 amount
		dp[i] = amount + 1
	}

	// 遍历总金额数
	for partialAmount := 1; partialAmount <= amount; partialAmount++ {
		// 遍历硬币
		for _, coin := range coins {
			if coin <= partialAmount {
				// 确保前一个状态是可达的
				if dp[partialAmount-coin] != amount+1 {
					dp[partialAmount] = min(dp[partialAmount-coin]+1, dp[partialAmount])
				}
			}
		}
	}

	if dp[amount] == amount+1 {
		return -1
	} else {
		return dp[amount]
	}
}

// 外层遍历硬币，内层遍历总金额数
func coinChangeImproved(coins []int, amount int) int {
	/*
		外层循环（选硬币）：我们一个一个地拿起硬币。
			第一次，我只允许使用 1元 硬币，去更新所有能凑出的金额的最少个数。
			第二次，我拿起 2元 硬币。此时，我可以单独用2元，也可以结合之前已经算好的“只用 1 元凑出的金额”来更新结果。
			第三次，我拿起 5元 硬币。同样，结合之前（只用 1 元和 2 元）算出的最优解来更新。
		内层循环（更新金额）：对于当前拿起的这枚硬币 coin，我们尝试把它加到所有可能的金额上。
			从 coin 开始一直遍历到 amount。
			公式：dp[i] = min(dp[i], dp[i - coin] + 1)
			意思是：凑出金额 i 的最少硬币数，要么是原来的方案（不用当前这枚硬币），要么是用一枚当前硬币 + 凑出剩余金额 i-coin 的最优方案。
	*/
	if amount == 0 {
		return 0
	}

	dp := make([]int, amount+1)
	// 初始化一个比任何可能答案都大的数
	for i := 1; i <= amount; i++ {
		dp[i] = amount + 1
	}

	// 外层遍历硬币，内层遍历总金额数
	for _, coin := range coins {
		for i := coin; i <= amount; i++ {
			// 要确保上一个状态是可达的
			if dp[i-coin] != amount+1 {
				dp[i] = min(dp[i-coin]+1, dp[i])
			}
		}
	}
	if dp[amount] == amount+1 {
		return -1
	} else {
		return dp[amount]
	}
}
