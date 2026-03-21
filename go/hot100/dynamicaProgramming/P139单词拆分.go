package dynamicProgramming

import "strings"

// 不使用 strings 包
func wordBreak(s string, wordDict []string) bool {
	// dp[i] 表示 s 的前 i 个字符组成的子字符串是否可以由 wordDict 中的单词拼接组成
	dp := make([]bool, len(s)+1)
	dp[0] = true
	// 转移方程
	for position := 1; position <= len(s); position++ {
		subS := s[:position]
		// 遍历字符串字典，查看是否有可达的上一个状态
		for _, vs := range wordDict {
			// 确保这个字典值不比 subS 长
			if len(vs) <= len(subS) {
				// 判断上一个状态是否可达
				if dp[len(subS)-len(vs)] {
					// 判读上一个状态是否可以通过拼接当前字典值以到达当前状态
					if subS[len(subS)-len(vs):] == vs {
						dp[position] = true
						break
					}
				}
			}
		}
	}

	return dp[len(s)]
}

// 使用 strings 包
func wordBreakUsingStrings(s string, wordDict []string) bool {
	// dp[i] 表示 s 的前 i 个字符组成的子字符串是否可以由 wordDict 中的单词拼接组成
	dp := make([]bool, len(s)+1)
	dp[0] = true

	// 转移方程
	for i := 1; i <= len(s); i++ {
		for _, word := range wordDict {
			wordLen := len(word)
			// 只有当当前长度足够容纳该单词，且前一个状态可达时，才进行匹配检查
			if i >= wordLen && dp[i-wordLen] {
				// 核心优化：使用 HasPrefix 检查 s 从 i-wordLen 开始的子串是否以 word 开头
				// 这等价于原代码中的 s[i-wordLen:i] == word
				if strings.HasPrefix(s[i-wordLen:i], word) {
					dp[i] = true
					break // 一旦找到一种可行的分割方式，即可跳出内层循环
				}
			}
		}
	}
	return dp[len(s)]
}
