package backTrap

func subsets(nums []int) [][]int {
	var res [][]int
	var tempRes []int
	n := len(nums)

	var backtrap func(i int)
	backtrap = func(start int) {
		// 每个节点都是一个合法子集，直接收集
		// ... 将 tempRes 展开为逐个元素，匹配可变参数
		res = append(res, append([]int{}, tempRes...))

		// 从 start 开始，枚举可以选择的元素
		for i := start; i < n; i++ {
			// 做选择
			tempRes = append(tempRes, nums[i])
			// 递归下一层
			backtrap(i + 1)
			// 撤销选择
			tempRes = tempRes[:len(tempRes)-1]
		}
	}

	backtrap(0)

	return res
}
