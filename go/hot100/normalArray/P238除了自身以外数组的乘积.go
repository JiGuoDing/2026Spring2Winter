package normalArray

// 核心思路：前缀积 × 后缀积
// 这是最优解法的核心思想 —— 将问题分解为左右两个子问题
func productExceptSelf(nums []int) []int {
	// 处理边界情况
	if len(nums) == 0 {
		return []int{}
	}

	n := len(nums)
	res := make([]int, n)

	// 前缀积和后缀积
	prefix, suffix := make([]int, n), make([]int, n)

	prefix[0], suffix[n-1] = 1, 1
	for i := 1; i < n; i++ {
		prefix[i] = prefix[i-1] * nums[i-1]
	}
	for j := n - 2; j >= 0; j-- {
		suffix[j] = suffix[j+1] * nums[j+1]
	}
	for k := 0; k < n; k++ {
		res[k] = prefix[k] * suffix[k]
	}

	return res
}

// productExceptSelf 计算除自身以外数组的乘积
// 时间复杂度: O(n) - 只需遍历数组常数次
// 空间复杂度: O(1) - 输出数组不算额外空间，仅使用常数个变量
func productExceptSelfImproved(nums []int) []int {
	n := len(nums)
	// 结果数组，同时用作存储前缀积
	result := make([]int, n)

	// ========== 第一阶段：计算前缀积 ==========
	// result[i] 暂存 nums[0] * nums[1] * ... * nums[i-1]
	// 即 i 位置左边所有元素的乘积

	result[0] = 1 // 第一个元素左边没有元素，乘积为1（乘法单位元）

	for i := 1; i < n; i++ {
		// 当前位置的前缀积 = 前一个位置的前缀积 × 前一个位置的元素值
		result[i] = result[i-1] * nums[i-1]
	}
	// 此时 result = [1, 1, 2, 6] (以[1,2,3,4]为例)

	// ========== 第二阶段：计算后缀积并与前缀积相乘 ==========
	// 使用一个变量 rightProduct 来动态维护当前位置右边的乘积
	// 避免使用额外数组存储后缀积，将空间复杂度优化到 O(1)

	rightProduct := 1 // 最后一个元素右边没有元素，初始为1

	// 从右往左遍历
	for i := n - 1; i >= 0; i-- {
		// 当前结果 = 前缀积(已存在result[i]) × 后缀积(rightProduct)
		result[i] *= rightProduct

		// 更新 rightProduct：将当前元素 nums[i] 纳入下一次的后缀积计算
		// 即下一次循环时，rightProduct 表示 i-1 位置右边所有元素的乘积
		rightProduct *= nums[i]
	}

	return result
}
