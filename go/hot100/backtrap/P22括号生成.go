package backTrap

// 不能用这个省略额外栈的方法，因为函数会修改参数传入的原始切片，导致主程序中的括号切片被意外修改
// func isValid(bracketSlice []byte) bool {
//     top := 0
//     for _, bracket := range bracketSlice {
//         switch bracket {
//         case '(', '[', '{':
//             bracketSlice[top] = bracket
//             top++
//         default:
//             if top == 0 {
//                 return false
//             }
//             // 弹出栈顶元素
//             open := bracketSlice[top-1]
//             if (bracket == ')' && open == '(') || (bracket == ']' && open == '[') || (bracket == '}' && open == '{') {
//                 top--
//             } else {
//                 return false
//             }
//         }
//     }

//     return top == 0
// }

func isValid(bracketSlice []byte) bool {
	stack := make([]byte, 0, len(bracketSlice))
	pairs := map[byte]byte{')': '(', ']': '[', '}': '{'}

	for _, b := range bracketSlice {
		switch b {
		case '(', '[', '{':
			stack = append(stack, b)
		default: // 右括号
			if len(stack) == 0 {
				return false
			}
			top := stack[len(stack)-1]
			stack = stack[:len(stack)-1]

			if pairs[b] != top {
				return false
			}
		}
	}
	return len(stack) == 0
}

func generateParenthesis(n int) []string {
	var res []string
	var bracketSlice []byte
	// brackets := []byte{'(', '[', '{', ')', ']', '}'}
	brackets := []byte{'(', ')'}

	var backtrap func()
	backtrap = func() {
		if len(bracketSlice) == 2*n {
			// 判断是否是合法的括号组合
			if isValid(bracketSlice) {
				// string() 转换会复制数据到新内存，因此不需要创建新的空切片复制数据
				res = append(res, string(bracketSlice))
			}
			return
		}

		for _, bracket := range brackets {
			bracketSlice = append(bracketSlice, bracket)
			backtrap()
			bracketSlice = bracketSlice[:len(bracketSlice)-1]
		}
	}

	backtrap()
	return res
}

// 优化剪枝方案
// *关键约束：
// * ( 的数量 < n 时，才能继续添加 (
// * ) 的数量 < ( 的数量时，才能添加 )
// * 这样完全不需要 isValid，直接保证生成的结果都是合法的，因为只有小括号。
func generateParenthesisImproved(n int) []string {
	var res []string
	buf := make([]byte, 0, 2*n)

	var backtrack func(open, close int)
	backtrack = func(open, close int) {
		// 长度满足时，直接加入结果（必然合法）
		if open+close == 2*n {
			res = append(res, string(buf))
			return
		}

		// 剪枝：左括号还没用完，可以加 (
		if open < n {
			buf = append(buf, '(')
			backtrack(open+1, close)
			buf = buf[:len(buf)-1]
		}

		// 剪枝：右括号数量 < 左括号数量，可以加 )
		if close < open {
			buf = append(buf, ')')
			backtrack(open, close+1)
			buf = buf[:len(buf)-1]
		}
	}

	backtrack(0, 0)
	return res
}
