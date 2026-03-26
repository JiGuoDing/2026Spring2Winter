package backTrap

// 131. 分割回文串
// 给你一个字符串 s，请你将 s 分割成一些子串，使每个子串都是回文串。返回 s 所有可能的分割方案。
//
// 示例 1:
// 输入：s = "aab"
// 输出：[["a","a","b"],["aa","b"]]
//
// 示例 2:
// 输入：s = "a"
// 输出：[["a"]]
//
// 提示:
// 1 <= s.length <= 16
// s 仅由小写英文字母组成

// partition 主函数，返回所有可能的回文分割方案
func partition(s string) [][]string {
	result := [][]string{}
	path := []string{}

	// isPalindrome 判断 s[left:right+1] 是否为回文串（双指针法）
	isPalindrome := func(left, right int) bool {
		for left < right {
			if s[left] != s[right] {
				return false
			}
			left++
			right--
		}
		return true
	}

	// backtracking 回溯函数
	// startIndex: 当前分割的起始位置
	backtracking := func(startIndex int) {}
	backtracking = func(startIndex int) {
		// 终止条件：已经切割到字符串末尾
		if startIndex >= len(s) {
			result = append(result, append([]string{}, path...))
			return
		}

		// 单层搜索逻辑：从 startIndex 开始，尝试在不同位置切割
		for i := startIndex; i < len(s); i++ {
			// 判断 [startIndex, i] 区间是否为回文串
			if isPalindrome(startIndex, i) {
				// 是回文串，加入路径
				path = append(path, s[startIndex:i+1])
				// 递归处理剩余部分
				backtracking(i + 1)
				// 回溯，撤销选择
				path = path[:len(path)-1]
			}
			// 如果不是回文串，则跳过这个切割点（剪枝）
		}
	}

	backtracking(0)
	return result
}

// 优化版本：使用动态规划预处理回文串判断
// dp[i][j] 表示 s[i:j+1] 是否为回文串
func partitionOptimized(s string) [][]string {
	n := len(s)
	result := [][]string{}
	path := []string{}

	// 1. 动态规划预处理：dp[i][j] 表示 s[i:j+1] 是否为回文串
	dp := make([][]bool, n)
	for i := range dp {
		dp[i] = make([]bool, n)
	}

	// 单个字符都是回文串
	for i := 0; i < n; i++ {
		dp[i][i] = true
	}

	// 长度为 2 的子串
	for i := 0; i < n-1; i++ {
		dp[i][i+1] = (s[i] == s[i+1])
	}

	// 长度 > 2 的子串
	for length := 3; length <= n; length++ {
		for i := 0; i <= n-length; i++ {
			j := i + length - 1
			dp[i][j] = (s[i] == s[j]) && dp[i+1][j-1]
		}
	}

	// 2. 回溯搜索所有分割方案
	var backtracking func(startIndex int)
	backtracking = func(startIndex int) {
		if startIndex >= n {
			temp := make([]string, len(path))
			copy(temp, path)
			result = append(result, temp)
			return
		}

		for i := startIndex; i < n; i++ {
			// 直接使用预计算的 dp 数组
			if dp[startIndex][i] {
				path = append(path, s[startIndex:i+1])
				backtracking(i + 1)
				path = path[:len(path)-1]
			}
		}
	}

	backtracking(0)
	return result
}
