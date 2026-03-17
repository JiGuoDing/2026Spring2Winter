package slidingWindow

func findAnagrams(s string, p string) []int {
	var res []int
	if len(s) == 0 || len(p) == 0 || len(p) > len(s) {
		return res
	}

	pCount := make(map[byte]int)
	sCount := make(map[byte]int)

	// 初始化 p 的计数
	for i := 0; i < len(p); i++ {
		pCount[p[i]]++
	}

	left := 0
	for right := 0; right < len(s); right++ {
		// 加入右边字符
		sCount[s[right]]++

		// 如果窗口大小超过 p 的长度，移除左边字符
		if right >= len(p) {
			sCount[s[left]]--
			if sCount[s[left]] == 0 {
				delete(sCount, s[left])
			}
			left++
		}

		// 比较两个 map 是否相等
		if equalMaps(sCount, pCount) {
			res = append(res, left)
		}
	}

	return res
}

func equalMaps(a, b map[byte]int) bool {
	if len(a) != len(b) {
		return false
	}
	for k, v := range a {
		if b[k] != v {
			return false
		}
	}
	return true
}
