package binaryTree

type TreeNode struct {
	Val   int
	Left  *TreeNode
	Right *TreeNode
}

// 递归方法
// 函数不断调用自身处理 Left，返回后处理当前 Val，再调用自身处理 Right。
func inorderTraversalRecursive(root *TreeNode) []int {
	var result []int

	// 定义内部递归函数
	var traverse func(node *TreeNode)
	traverse = func(node *TreeNode) {
		if node == nil {
			return
		}
		// 遍历左子树
		traverse(node.Left)
		// 访问根节点
		result = append(result, node.Val)
		// 遍历右子树
		traverse(node.Right)
	}

	traverse(root)
	return result
}

// 迭代方法
// 使用栈来手动模拟递归调用的过程。核心逻辑是：
// 1. 一直向左走，将沿途节点压入栈中。
// 2. 当无法向左时，弹出栈顶节点（即最左边的节点），访问它。
// 3. 然后转向该节点的右子树，重复上述过程。
func inorderTraversal(root *TreeNode) []int {
	var result []int
	if root == nil {
		return result
	}

	stack := []*TreeNode{}
	curr := root

	// 当前节点不为空或者栈不为空时循环
	for curr != nil || len(stack) > 0 {
		// 尽可能向左遍历，并将节点压入栈
		for curr != nil {
			stack = append(stack, curr)
			curr = curr.Left
		}

		// 弹出栈顶元素 (最左边的节点)
		curr = stack[len(stack)-1]
		stack = stack[:len(stack)-1]

		// 访问该节点
		result = append(result, curr.Val)
		// 转向其右子树
		curr = curr.Right
	}

	return result
}
