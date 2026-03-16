package binaryTree

func diameterOfBinaryTree(root *TreeNode) int {
	if root == nil {
		return 0
	}

	diameter := 0
	var dive func(node *TreeNode) int
	dive = func(node *TreeNode) int {
		if node == nil {
			return 0
		}
		leftDepth := dive(node.Left)
		rightDepth := dive(node.Right)
		localDiameter := leftDepth + rightDepth
		diameter = max(diameter, localDiameter)
		return max(leftDepth, rightDepth) + 1
	}

	dive(root)

	return diameter

}
