package normalArray

import (
	"cmp"
	"slices"
)

func merge(intervals [][]int) [][]int {
	var res [][]int

	// 按区间起点升序排列区间
	slices.SortFunc(intervals, func(a, b []int) int {
		return cmp.Compare(a[0], b[0])
	})

	// 指示当前处理的区间的起点和终点，初始时为第一个区间的起点和终点
	currentStart := intervals[0][0]
	currentEnd := intervals[0][1]

	for _, interval := range intervals[1:] {
		if interval[0] > currentEnd {
			// 如果这个区间的起点大于当前记录的区间的终点，将当前记录的区间加入答案中，并从这个区间重新开始
			res = append(res, []int{currentStart, currentEnd})
			currentStart = interval[0]
			currentEnd = interval[1]
		} else {
			// 如果这个区间的起点小与等于当前记录区间的终点，说明可以合并，更新当前记录的区间的终点为两个区间的终点的较大值
			currentEnd = max(currentEnd, interval[1])
		}
	}

	// 把最终区间也加入结果集中
	res = append(res, []int{currentStart, currentEnd})

	return res
}
