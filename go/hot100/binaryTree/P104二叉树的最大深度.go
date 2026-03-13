package binarytree

func maxDepth(root *TreeNode) int {
	depthMax := 0

	// node 表示当前节点，depth 表示当前层深度
	var traverse func(node *TreeNode, depth int)
	traverse = func(node *TreeNode, depth int) {
		if node == nil {
			return
		}
		traverse(node.Left, depth+1)
		depthMax = max(depthMax, depth+1)
		traverse(node.Right, depth+1)
	}

	traverse(root, 0)
	return depthMax
}

func maxDepthImproved(root *TreeNode) int {
	if root == nil {
		return 0
	}
	// 递归计算左右子树的最大深度
	leftDepth := maxDepth(root.Left)
	rightDepth := maxDepth(root.Right)

	// 返回较大者 + 1 (当前节点)
	if leftDepth > rightDepth {
		return leftDepth + 1
	}
	return rightDepth + 1
}
