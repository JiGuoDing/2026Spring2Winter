package twopointers

func moveZeroes(nums []int) {
	// left 表示已处理好的序列的末尾，right 表示未处理的序列的开头
	// left 左侧均为非 0 数，left 指向第一个 0
	// left 和 right 中间全是 0
	// left 与 right 共同推进，每遇到一个 0 就把它夹到中间
	left, right, n := 0, 0, len(nums)

	for right < n {
		if nums[right] != 0 {
			nums[left], nums[right] = nums[right], nums[left]
			left++
		}
		right++
	}
}
