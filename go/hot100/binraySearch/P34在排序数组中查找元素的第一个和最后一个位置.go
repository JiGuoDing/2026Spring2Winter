package binraysearch

// 在排序数组中寻找 target 的第一个位置
func binarySearchFirst(nums []int, target int) int {
	if len(nums) == 0 {
		return -1
	}

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

	if ans < len(nums) && nums[ans] == target {
		return ans
	} else {
		return -1
	}
}

// 在排序数组中寻找 target 的最后一个位置
func binarySearchLast(nums []int, target int) int {
	if len(nums) == 0 {
		return -1
	}

	left, right, ans := 0, len(nums)-1, -1
	for left <= right {
		mid := (right-left)/2 + left
		if nums[mid] <= target {
			ans = mid
			left = mid + 1
		} else {
			right = mid - 1
		}
	}

	if ans > -1 && nums[ans] == target {
		return ans
	} else {
		return -1
	}
}

// 非递减序列中查找元素的第一个和最后一个位置
func searchRange(nums []int, target int) []int {
	return []int{binarySearchFirst(nums, target), binarySearchLast(nums, target)}
}
