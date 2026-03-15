package binarySearch

import "log/slog"

// 在旋转后的升序序列中找到旋转点 (第一个比前一个数小的数所对应的索引)
func binarySearchSpin(nums []int) int {
	// 旋转后的序列中 nums[0] 一定 > nums[len(nums)-1]
	left, right := 0, len(nums)-1
	for left < right {
		mid := (right-left)/2 + left
		if nums[mid] > nums[left] {
			// 说明 left -> mid 是升序序列，旋转点在 mid -> right 之间
			left = mid
		} else {
			// 说明 left -> 不是升序序列，旋转点在 left -> mid 之间
			right = mid
		}
	}

	return left
}

// 标准二分搜索，返回序列中第一个目标值的索引
func binarySearchP33(nums []int, target int) int {
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
		return -1
	}
	if nums[ans] == target {
		return ans
	}
	return -1
}

func Search(nums []int, target int) int {
	if len(nums) == 1 {
		if nums[0] == target {
			return 0
		}
		return -1
	}

	spinPosition := binarySearchSpin(nums)
	slog.Info("Spin Position: ", "spinPosition", spinPosition)
	ans1, ans2 := binarySearchP33(nums[:spinPosition+1], target), binarySearchP33(nums[spinPosition+1:], target)

	if ans1 != -1 {
		return ans1
	}
	if ans2 != -1 {
		// ans2 是在子串中的索引，需要添加偏移量 spinPosition + 1
		return ans2 + spinPosition + 1
	}
	return -1
}
