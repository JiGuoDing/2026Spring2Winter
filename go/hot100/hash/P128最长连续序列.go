package hash

func longestConsecutive(nums []int) int {
	if len(nums) == 0 {
		return 0
	}

	var maxConsecutiveLength int
	numMap := make(map[int]bool, len(nums))
	for _, num := range nums {
		numMap[num] = true
	}

	for num := range numMap {
		// 只对序列的“起点”进行匹配
		// 如果 num - 1 存在，说明 num 只是某个序列的中间节点，直接跳过
		if !numMap[num-1] {
			currentNum := num
			currentConsecutiveLenghth := 1

			// 向后寻找 currentNum + 1 是否存在
			for numMap[currentNum+1] {
				currentNum++
				currentConsecutiveLenghth++
			}

			maxConsecutiveLength = max(currentConsecutiveLenghth, maxConsecutiveLength)
		}
	}

	return maxConsecutiveLength
}
