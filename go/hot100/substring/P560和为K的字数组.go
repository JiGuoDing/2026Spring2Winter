package substring

func subarraySum(nums []int, k int) int {
	cnt := 0
	for start := range nums {
		sum := 0
		// 从 start 处往前推，这样得到 sum = [end, start] 后就可以在 O(1) 时间得到 sum = [end-1, start]
		for end := start; end >= 0; end-- {
			sum += nums[end]
			if sum == k {
				cnt++
			}
		}
	}

	return cnt
}
