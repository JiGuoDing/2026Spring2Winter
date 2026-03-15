package binarySearch

func binarySearch(nums []int, target int) bool {
	left, right, ans := 0, len(nums)-1, len(nums)
	for left <= right {
		mid := (right-left)/2 + left
		if nums[mid] >= target {
			ans = mid
			right = mid - 1
		} else {
			left = mid + 1
		}
	}

	if ans == len(nums) {
		return false
	} else {
		return nums[ans] == target
	}
}

func searchMatrix(matrix [][]int, target int) bool {
	// 首先找到 target 所在行
	firstSequence := make([]int, len(matrix))
	for rowNum, row := range matrix {
		firstSequence[rowNum] = row[0]
	}

	lastFirst, targetRowNum := firstSequence[0], 0
	if len(matrix) > 1 {
		for i := 1; i < len(matrix); i++ {
			currentFirst := firstSequence[i]
			if lastFirst <= target && currentFirst > target {
				// target 大于等于上一行第一个数且小于当前行第一个数，一定在上一行，直接退出
				targetRowNum = i - 1
				break
			} else if currentFirst <= target {
				// target 小于等于当前行第一个数，一定在当前行或之后
				targetRowNum = i
			}
			lastFirst = currentFirst
		}
	}

	targetRow := matrix[targetRowNum]
	return binarySearch(targetRow, target)
}
