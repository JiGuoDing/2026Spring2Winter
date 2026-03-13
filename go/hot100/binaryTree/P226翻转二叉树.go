package binarytree

import "container/list"

func invertTree(root *TreeNode) *TreeNode {
	if root == nil {
		return nil
	}
	root.Left, root.Right = root.Right, root.Left
	invertTree(root.Left)
	invertTree(root.Right)

	return root
}

func invertTreeBFS(root *TreeNode) *TreeNode {
	if root == nil {
		return nil
	}

	queue := list.New()
	queue.PushBack(root)

	return root
}
