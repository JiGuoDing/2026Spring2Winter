package hash

import "slices"

// 为一个字符串排序字符
func sort_ch(str string) string {
	// 转换为 byte 切片
	byteSlice := []byte(str)
	// 切片排序 slices.Sort() 底层是 pdqSort，O(NlogN)
	slices.Sort(byteSlice)
	return string(byteSlice)
}

func groupAnagrams(strs []string) [][]string {
	var res [][]string
	// 记录出现了哪些字母组合及其在 res 中的索引
	strMap := make(map[string]int, len(strs))

	for _, str := range strs {
		tempStr := sort_ch(str)
		if v, ok := strMap[tempStr]; !ok {
			// map 中没有记录当前字母组合，说明这个组合是第一次出现，将其加入 res 和 map
			res = append(res, []string{str})
			strMap[tempStr] = len(res) - 1
		} else {
			// map 中已有当前字母组合
			// 检查 res 中是否已有当前组合的当前顺序形式
			// for _, recorededStr := range res[v] {
			//     if recorededStr == str {
			//         continue
			//     }
			// }
			res[v] = append(res[v], str)
		}
	}
	return res
}
