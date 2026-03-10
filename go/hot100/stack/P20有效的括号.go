package stack

func isValid(s string) bool {
	stack := make([]rune, 0, len(s))
	for _, ch := range s {
		switch ch {
		case '(', '[', '{':
			stack = append(stack, ch)
		case ')', ']', '}':
			if len(stack) == 0 {
				return false
			} else {
				if ch == ')' && stack[len(stack)-1] != '(' {
					return false
				} else if ch == ']' && stack[len(stack)-1] != '[' {
					return false
				} else if ch == '}' && stack[len(stack)-1] != '{' {
					return false
				}
				stack = stack[:len(stack)-1]
			}
		default:
			return false
		}
	}
	return len(stack) == 0
}

func isValidImproved(s string) bool {
	// 空间复杂度限制为 O(1)
	// 写指针一定不比读指针快，因此可以确保正确性
	// top 指向下一个可以覆盖的位置
	top := 0
	bs := []rune(s)

	for _, ch := range s {
		switch ch {
		case '(', '[', '{':
			bs[top] = ch
			top++
		default:
			if top == 0 {
				return false
			}
			// 弹出栈顶元素
			open := bs[top-1]
			if (ch == ')' && open == '(') || (ch == ']' && open == '[') || (ch == '}' && open == '{') {
				top--
			} else {
				return false
			}
		}
	}
	return top == 0
}
