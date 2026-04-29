package interviewIssue

// 给定一个数组，找出其中频次大于三分之一的元素
// 这道题是经典的摩尔投票法的进阶应用
// 算法分为两个阶段：
// 阶段一：投票找候选人
// 阶段二：验证候选人
func majorityElement(nums []int) []int {
	if len(nums) == 0 {
		return []int{}
	}

	// 阶段一：摩尔投票找出最多的两个候选人
	var cand1, cand2 int
	count1, count2 := 0, 0

	for _, num := range nums {
		if num == cand1 {
			count1++
		} else if num == cand2 {
			count2++
		} else if count1 == 0 {
			cand1 = num
			count1 = 1
		} else if count2 == 0 {
			cand2 = num
			count2 = 1
		} else {
			// num 与 cand1, cand2 都不相同，抵消一次
			count1--
			count2--
		}
	}

	// 阶段二：重新计票，验证候选人是否频次大于三分之一
	var res []int
	for _, num := range nums {
		if num == cand1 {
			count1++
		} else if num == cand2 {
			count2++
		}
	}
	if count1 > len(nums)/3 {
		res = append(res, cand1)
	}
	if count2 > len(nums)/3 && cand2 != cand1 {
		res = append(res, cand2)
	}
	return res
}
