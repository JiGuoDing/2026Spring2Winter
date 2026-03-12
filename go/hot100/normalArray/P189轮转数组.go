package normalarray

func rotate(nums []int, k int) {
	// 删去超出一次循环的部分
	n := len(nums)

	// 当 gcd(n, k) > 1 时，存在多个独立循环，但代码只从位置 0 出发，其他循环的元素永远不会被处理。
	cnt := 0   // 已处理元素数
	start := 0 // 每个独立循环的起点

	for cnt < n {
		current := start
		prev := nums[start]

		for {
			next := (current + k) % n
			nums[next], prev = prev, nums[next]
			current = next
			cnt++
			if current == start { // 回到起点，本循环结束
				break
			}
		}
		start++ // 进入下一个独立循环
	}
}
