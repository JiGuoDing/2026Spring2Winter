package backtrap

func combinationSum(candidates []int, target int) [][]int {
	var res [][]int
	accumulator := 0
	combination := []int{}

	var backtrap func(start int)
	backtrap = func(start int) {
		if accumulator == target {
			res = append(res, append([]int{}, combination...))
			return
		}
		// 超过目标值，剪枝返回，避免无限递归
		if accumulator > target {
			return
		}

		// 从 i 开始，避免使用之前已经用过的数字
		for i := start; i < len(candidates); i++ {
			combination = append(combination, candidates[i])
			accumulator += candidates[i]

			// 进入下一层，传入 i 而非 i+1，因为同一个元素允许重复使用
			backtrap(i)

			combination = combination[:len(combination)-1]
			accumulator -= candidates[i]
		}
	}

	backtrap(0)

	return res
}
