package greedy

func maxProfit(prices []int) int {
	lowest, highestProfit := prices[0], 0
	for _, price := range prices {
		// 每天都假设在今天卖出，并且已经记录了今天前的最低点，可以得到如果今天卖出，能赚到的最多钱
		if price < lowest {
			lowest = price
		} else {
			highestProfit = max(highestProfit, price-lowest)
		}
	}

	return highestProfit
}
