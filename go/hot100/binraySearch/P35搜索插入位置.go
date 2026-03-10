package binraysearch

// 二分查找模板
func SearchInsert(nums []int, target int) int {
	left, right, ans := 0, len(nums)-1, len(nums)
	// 这里的 ans 与 if 条件可以决定返回第一个还是最后一个 target
	// 如果是返回第一个 target，则 ans 初始值为 len(nums)，条件为 nums[mid] >= target 更新 ans，即从右往左收缩，ans 会停在第一个 >= target 的位置
	// 如果是返回最后一个 target，则 ans 初始值为 -1，条件为 nums[mid] <= target 更新 ans，即从左往右收缩，ans 会停在最后一个 <= target 的位置

	for left <= right {
		mid := (right-left)/2 + left
		if nums[mid] >= target {
			// 判断满足条件，更新 ans
			ans = mid
			right = mid - 1
		} else {
			left = mid + 1
		}
	}

	return ans
}

func binarySearchEasy(nums []int, target int) int {
	left, right := 0, 0
	for left <= right {
		mid := (right-left)/2 + left
		if nums[mid] == target {
			return mid
		} else if nums[mid] > target {
			right = mid - 1
		} else {
			left = mid + 1
		}
	}

	// 没找到就返回 -1
	return -1
}
