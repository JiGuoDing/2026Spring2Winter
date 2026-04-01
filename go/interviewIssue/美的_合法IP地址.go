package interviewIssue

import (
	"strconv"
	"strings"
)

// 参数 s：输入的数字字符串
// 返回值：所有合法的IP地址字符串切片
func RestoreIpAddress(s string) []string {
	var res []string
	n := len(s)

	if len(s) < 4 || len(s) > 12 {
		return res
	}

	// 回溯函数
	// 无需传递冗余参数，直接捕获外部的 s、res、n
	// start：当前分段的起始索引
	// segments：已经分割完成的IP段数
	// path：临时存储当前分割的合法IP段
	var backtrack func(start, segments int, path []string)
	backtrack = func(start, segments int, path []string) {
		// 终止条件：分割出 4 段，且遍历完所有字符
		if segments == 4 {
			// 必须遍历完所有字符，才是合法 IP
			if start == n {
				res = append(res, strings.Join(path, "."))
			}
			return
		}

		// 每段最多截取 3 个字符
		for i := start; i < start+3 && i < n; i++ {
			segment := s[start : i+1]
			if !isValid(segment) {
				continue
			}
			backtrack(i+1, segments+1, append(path, segment))
		}
	}

	backtrack(0, 0, []string{})
	return res
}

func isValid(seg string) bool {
	if len(seg) > 1 && seg[0] == '0' {
		return false
	}
	num, _ := strconv.Atoi(seg)
	return num >= 0 && num <= 255
}
