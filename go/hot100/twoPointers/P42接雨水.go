package twopointers

type pillar struct {
	height   int
	position int
}

// 使用分治思想
func trap(height []int) int {
	if len(height) < 3 {
		return 0
	}

	res := 0
	// // 找到最高的柱子
	// var pillars []pillar
	// for position, h := range height {
	//     pillars = append(pillars, pillar{h, position})
	// }
	// // 按柱子高度降序排列
	// slices.SortFunc(pillars, func(a, b pillar) int {
	// 	return -1 * cmp.Compare(a.height, b.height)
	// })

	// ----- 优化 ---------------
	// 优化点：用 O(N) 的一次遍历，直接找出“最高”和“次高”柱子的索引 (max1 和 max2)
	// 完全丢弃了原来耗时的 []pillar 切片分配和 slices.SortFunc
	max1, max2 := 0, 1 // 假设索引 0 是最高，索引 1 是次高
	if height[1] > height[0] {
		max1, max2 = 1, 0
	}

	// 从第三个柱子开始遍历，更新最高和次高的索引
	for i := 2; i < len(height); i++ {
		if height[i] > height[max1] {
			// 如果当前柱子比最高的还高，那么原来的最高退居二线变成次高，当前变成最高
			max2 = max1
			max1 = i
		} else if height[i] >= height[max2] {
			// 如果当前柱子没有最高的高，但是比次高的高，那就更新次高
			// 注意这里用 >=，处理有两个柱子一样高的情况（比如 [5, 5, 5]）
			max2 = i
		}
	}

	// 初始化 left 和 right
	left, right := min(max1, max2), max(max1, max2)
	res += height[max2] * (right - left - 1)
	for i := left + 1; i < right; i++ {
		res -= height[i]
	}

	res += trap(height[:left+1])
	res += trap(height[right:])

	return res
}

// 按列计算每一列的接水量
func column(height []int) int {
	n, ans := len(height), 0
	if n == 0 {
		return 0
	}

	// 找到每一列的左边最高和右边最高柱子的高度，用较小的那一个减去当前柱子的高度，就是当前列的接水量
	leftMax := make([]int, n)
	leftMax[0] = height[0]
	for i := 1; i < n; i++ {
		leftMax[i] = max(leftMax[i-1], height[i])
	}

	rightMax := make([]int, n)
	rightMax[n-1] = height[n-1]
	for i := n - 2; i >= 0; i-- {
		rightMax[i] = max(rightMax[i+1], height[i])
	}

	for i, h := range height {
		ans += min(leftMax[i], rightMax[i]) - h
	}
	return ans
}
