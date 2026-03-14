package stack

import (
	"strconv"
	"strings"
	"unicode"
)

func decodeString(s string) string {
	if len(s) == 0 {
		return s
	}
	// 找到最后一个 [ 的位置 (一定是局部最内层左括号)
	for strings.Contains(s, "[") {
		lastLeftIndex := strings.LastIndex(s, "[")
		if lastLeftIndex == -1 {
			break
		}
		// 最后一个 [ 对应的 ] 距离它的偏移量
		rightOffset := strings.Index(s[lastLeftIndex:], "]")
		if rightOffset == -1 {
			break
		}
		rightIndex := lastLeftIndex + rightOffset
		// 提取括号内的内容
		innerStr := s[lastLeftIndex+1 : rightIndex]

		// 提取括号前的数字（从 lastLeftIndex-1 开始向前）
		digitStart := lastLeftIndex - 1
		for digitStart >= 0 && s[digitStart] >= '0' && s[digitStart] <= '9' {
			digitStart--
		}
		digitStart++ // 回到第一个数字字符
		numStr := s[digitStart:lastLeftIndex]
		if len(numStr) == 0 {
			break // 没有数字，退出
		}
		repeatNum, err := strconv.Atoi(numStr)
		if err != nil {
			break // 解析失败，退出
		}

		// 构建新字符串（使用 Builder 优化性能）
		var builder strings.Builder
		builder.Grow(len(s)) // 预分配容量
		builder.WriteString(s[:digitStart])

		if repeatNum > 0 {
			builder.WriteString(strings.Repeat(innerStr, repeatNum))
		}

		builder.WriteString(s[rightIndex+1:])
		s = builder.String()
	}

	return s
}

// 使用栈解码字符串
func decodeStringStack(s string) string {
	// 1. 初始化栈和状态变量
	numStack := make([]int, 0)    // 存储内部字符串重复次数
	strStack := make([]string, 0) // 存储外层字符串前缀
	currentNum := 0               // 当前正在解析的数字
	// 用指针：避免复制，Write 等方法需要指针接收者
	currentStr := &strings.Builder{} // 当前层正在构建的字符串

	// 2. 遍历字符串的每个字符
	for _, ch := range s {
		if unicode.IsDigit(ch) {
			// 情况一：数字字符 -> 累加构建多位数
			// 例如："123" -> 1 -> 12 -> 123
			currentNum = currentNum*10 + int(ch-'0')
		} else if ch == '[' {
			// 情况二：左括号 -> 保存当前状态，进入内层
			// 将当前的重复次数和字符串前缀入栈
			numStack = append(numStack, currentNum)
			strStack = append(strStack, currentStr.String())

			// 重置状态
			currentNum = 0
			currentStr = &strings.Builder{}
		} else if ch == ']' {
			// 情况三：右括号 -> 恢复外层状态，合并结果
			// 弹出栈顶的重复次数
			repeatNum := numStack[len(numStack)-1]
			numStack = numStack[:len(numStack)-1]

			// 弹出栈顶的外层字符串前缀
			lastStr := strStack[len(strStack)-1]
			strStack = strStack[:len(strStack)-1]

			// 构建新的字符串：外层前缀 + 内层字符串*重复次数
			newStr := &strings.Builder{}
			newStr.WriteString(lastStr)
			newStr.WriteString(strings.Repeat(currentStr.String(), repeatNum))

			// 更新当前字符串为合并后的结果
			currentStr = newStr
		} else {
			// 情况四：普通字符 -> 直接添加到当前字符串
			currentStr.WriteRune(ch)
		}
	}

	return currentStr.String()
}
