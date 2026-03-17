package slidingWindow

func lengthOfLongestSubstring(s string) int {
	left, right, n := 0, 0, len(s)
	// 指示当前窗口下有哪些字符出现，并记录其索引位置
	chMap := make(map[byte]int, n)
	maxRes := 0

	for left < n && right < n {
		if index, ok := chMap[s[right]]; !ok {
			// 当前 map 中没有该字符，记录该字符，窗口右端向右延伸
			chMap[s[right]] = right
			maxRes = max(maxRes, right-left+1)
		} else {
			// 当前 map 中有该字符，窗口左端向右收缩
			for i := left; i <= index; i++ {
				delete(chMap, s[i])
			}
			left = index + 1
		}
		// 将当前字符加入 map 中
		chMap[s[right]] = right
		right++
	}
	return maxRes
}
