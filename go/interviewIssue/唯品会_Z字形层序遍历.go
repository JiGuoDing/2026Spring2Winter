package interviewIssue

import "container/list"

type TreeNode struct {
	Val   int
	Left  *TreeNode
	Right *TreeNode
}

// Z字形层序遍历二叉树，返回节点值的遍历列表
//
// 题目描述：
// 给定一棵二叉树，按照Z字形（锯齿形）的顺序返回其层序遍历结果。
// 即第一层从左到右，第二层从右到左，第三层从左到右，以此类推。
//
// 解题思路：
// 1. 使用BFS（广度优先搜索）进行层序遍历
// 2. 通过队列存储每一层的节点
// 3. 使用布尔标志位记录当前层的遍历方向
// 4. 奇数层（层数从1开始）正常顺序收集节点值
// 5. 偶数层反转顺序收集节点值
//
// 算法流程：
// - 初始化队列，将根节点入队
// - 循环处理每一层：
//   - 记录当前层节点数量
//   - 遍历当前层所有节点，收集节点值
//   - 将下一层节点入队（先左后右）
//   - 如果是偶数层，反转当前层结果
//
// 时间复杂度：O(n)，其中n是二叉树节点数，每个节点访问一次
// 空间复杂度：O(n)，队列最多存储一层的节点数（最坏情况是满二叉树的叶子层约n/2个节点）
func Ztraverse(root *TreeNode) []int {
	if root == nil {
		return []int{}
	}

	result := []int{}
	queue := list.New()
	queue.PushBack(root)

	// 标志位：true表示从左到右，false表示从右到左
	// 初始为true，第一层从左到右
	isLeftToRight := true

	for queue.Len() > 0 {
		// 当前层的节点数
		levelSize := queue.Len()
		// 当前层的节点值
		currentLevel := make([]int, levelSize)

		// 遍历当前层的所有节点
		for i := range levelSize {
			// 从队列头部取出节点
			element := queue.Front()
			queue.Remove(element)
			node := element.Value.(*TreeNode)

			// 根据遍历方向决定存放位置
			if isLeftToRight {
				// 从左到右：顺序存放
				currentLevel[i] = node.Val
			} else {
				// 从右到左：逆序存放
				currentLevel[levelSize-1-i] = node.Val
			}

			// 将下一层节点入队（先左后右）
			if node.Left != nil {
				queue.PushBack(node.Left)
			}
			if node.Right != nil {
				queue.PushBack(node.Right)
			}
		}

		// 将当前层结果加入最终结果
		result = append(result, currentLevel...)

		// 切换遍历方向
		isLeftToRight = !isLeftToRight
	}

	return result
}

// Z字形层序遍历二叉树（使用双栈法）
//
// 解题思路：
// 使用两个栈交替处理奇数层和偶数层：
// - 栈1存储奇数层节点（从左到右遍历）
// - 栈2存储偶数层节点（从右到左遍历）
//
// 算法流程：
// 1. 栈1先入栈根节点
// 2. 处理栈1（奇数层）：
//   - 出栈节点，收集值
//   - 先压入左子节点到栈2，再压入右子节点
//
// 3. 处理栈2（偶数层）：
//   - 出栈节点，收集值
//   - 先压入右子节点到栈1，再压入左子节点
//
// 4. 重复直到两个栈都为空
//
// 时间复杂度：O(n)
// 空间复杂度：O(n)
func ZtraverseWithDoubleStack(root *TreeNode) []int {
	if root == nil {
		return []int{}
	}

	result := []int{}
	// 奇数层栈（从左到右）
	oddStack := []*TreeNode{root}
	// 偶数层栈（从右到左）
	evenStack := []*TreeNode{}

	for len(oddStack) > 0 || len(evenStack) > 0 {
		// 处理奇数层（从左到右）
		for len(oddStack) > 0 {
			// 出栈
			node := oddStack[len(oddStack)-1]
			oddStack = oddStack[:len(oddStack)-1]

			result = append(result, node.Val)

			// 先左后右入栈，这样出栈时是右左顺序（偶数层需要）
			if node.Left != nil {
				evenStack = append(evenStack, node.Left)
			}
			if node.Right != nil {
				evenStack = append(evenStack, node.Right)
			}
		}

		// 处理偶数层（从右到左）
		for len(evenStack) > 0 {
			// 出栈
			node := evenStack[len(evenStack)-1]
			evenStack = evenStack[:len(evenStack)-1]

			result = append(result, node.Val)

			// 先右后左入栈，这样出栈时是左右顺序（奇数层需要）
			if node.Right != nil {
				oddStack = append(oddStack, node.Right)
			}
			if node.Left != nil {
				oddStack = append(oddStack, node.Left)
			}
		}
	}

	return result
}
