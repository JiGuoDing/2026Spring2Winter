package backTrap

func permute(nums []int) [][]int {
	var res [][]int
	n := len(nums)
	// 当前路径，记录当前已经选择的数字
	var path []int
	// 标记 nums[i] 是否已经加入到 path 中
	// used[i] == true 表示 nums[i] 已经在当前路径中，不能重复选
	used := make([]bool, n)

	// 定义回溯函数，不需要参数，因为可以直接访问外部作用域的 nums, path, used, res
	// 也可以将 path 和 used 作为参数传递，但在 Go 中闭包写法更简洁
	var backtrack func()
	backtrack = func() {
		// 终止条件：路径长度等于数组长度，说明找到一个完整的排列
		if len(path) == n {
			// 要复制一份，否则后续修改会影响结果
			// 因为 path 是引用类型，后续的回溯操作会修改 path 底层数组，如果不复制，res 中存的都是同一个空切片或错误数据
			// tmp := make([]int, n)
			// copy(tmp, path)
			// res = append(res, tmp)
			res = append(res, append([]int{}, path...))
			return
		}

		// 遍历选择列表，遍历数组中的每一个数字，尝试将其加入当前路径
		for i := 0; i < n; i++ {
			// 如果当前数字已经在路径中，跳过
			if used[i] {
				continue
			}

			// 1. 将数字加入路径
			path = append(path, nums[i])
			// 2. 标记该数字已使用
			used[i] = true

			// 进入下一层决策树
			backtrack()

			// 撤销选择
			path = path[:len(path)-1]
			used[i] = false
		}
	}

	backtrack()
	return res
}

// 回溯通用框架：
// void backtrack(路径, 选择列表):
//     if 满足结束条件:
//         结果集.add(路径)
//         return

//     for 选择 in 选择列表:
//         做选择
//         backtrack(路径, 选择列表)
//         撤销选择
