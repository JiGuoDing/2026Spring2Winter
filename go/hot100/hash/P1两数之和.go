package hash

func twoSum(nums []int, target int) []int {
	// 存储一个整数及其下标
	numMap := make(map[int]int, len(nums)+1)
	for idx, num := range nums {
		if remain_idx, ok := numMap[target-num]; ok {
			if idx == remain_idx {
				continue
			}
			return []int{idx, remain_idx}
		}
		numMap[num] = idx
	}
	return []int{}
}
