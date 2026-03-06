package twopointers

func maxArea(height []int) int {
	var maxAreaRes int
	left, right := 0, len(height)-1
	for left < right {
		xLen := right - left
		yHeight := min(height[left], height[right])
		maxAreaRes = max(xLen*yHeight, maxAreaRes)

		// 一定是移动较低的那一边，应为如果移动较高的那一边的话，无论如何移动，得到的结果都不可能比当前结果更优
		if height[left] > height[right] {
			right--
		} else {
			left++
		}
	}

	return maxAreaRes
}
