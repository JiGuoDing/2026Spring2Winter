package greedy

func canJump(nums []int) bool {
	// position := 0
	// for position < len(nums) {
	// 	if position+nums[position] >= len(nums)-1 {
	// 		return true
	// 	}
	// 	// 找出当前步和下一步能到的最远的距离
	// 	nextPosition := position
	// 	tempMaxDistance := 0
	// 	for i := position + 1; i <= min(position+nums[position], len(nums)-1); i++ {
	// 		if i+nums[i] > tempMaxDistance {
	// 			tempMaxDistance = i + nums[i]
	// 			nextPosition = i
	// 		}
	// 	}

	// 	if nextPosition == position {
	// 		// 说明当前步和下一步能到的最远的距离没有变化，说明不能到达更远的位置
	// 		return false
	// 	}
	// 	position = nextPosition
	// }

	// return true

	// 优化方案
	maxReach := 0
	for i := range nums {
		if i > maxReach {
			return false
		}

		maxReach = max(maxReach, i+nums[i])
	}

	return true
}
