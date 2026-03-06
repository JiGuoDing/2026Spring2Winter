package twopointers

import (
	"sort"
)

func threeSum(nums []int) [][]int {
	sort.Ints(nums)
	n := len(nums)
	var res [][]int
	for first := 0; first < n; first++ {
		// 需要和上一次枚举的数不同，因为答案不能重复
		if first > 0 && nums[first] == nums[first-1] {
			continue
		}
		third := n - 1
		target := 0 - nums[first]
		for second := first + 1; second < n; second++ {
			// 需要和上一次枚举的数不同
			// 必须要 second > first + 1，因为当 second == first + 1 时，
			// 是第二个循环的第一次遍历，不存在重复的情况，nums[second-1] 即 nums[first]
			if second > first+1 && nums[second] == nums[second-1] {
				continue
			}
			for second < third && nums[second]+nums[third] > target {
				third--
			}
			if second == third {
				break
			}
			if nums[second]+nums[third] == target {
				res = append(res, []int{nums[first], nums[second], nums[third]})
			}
		}
	}
	return res
}
