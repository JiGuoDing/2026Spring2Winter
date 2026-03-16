package backTrap

func letterCombinations(digits string) []string {
	// 处理边界情况
	if len(digits) == 0 {
		return []string{}
	}

	// Go 支持在切片/数组字面量中指定下标，未指定的位置自动补零值
	digit2Letters := [][]byte{
		2: []byte("abc"),
		3: []byte("def"),
		4: []byte("ghi"),
		5: []byte("jkl"),
		6: []byte("mno"),
		7: []byte("pqrs"),
		8: []byte("tuv"),
		9: []byte("wxyz"),
	}

	var res []string
	var combination []byte

	var backtrap func(i int)
	backtrap = func(i int) {
		if len(combination) == len(digits) {
			combinationStr := string(combination)
			res = append(res, combinationStr)
			// 注意这里万万不能清空 combination，下面的 combination = combination[:len(combination)-1] 会撤销选择，也即回溯
			// backtracking 的"撤销"已经由 for 循环里的 combination[:len(combination)-1] 负责了
			return
		}

		for _, letter := range digit2Letters[digits[i]-'0'] {
			combination = append(combination, letter)
			backtrap(i + 1)
			combination = combination[:len(combination)-1]
		}
	}

	backtrap(0)

	return res
}
