package binaryTree

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

	for queue.Len() > 0 {
		// 取出队头节点
		node := queue.Front().Value.(*TreeNode)
		queue.Remove(queue.Front())
		// 交换左子树和右子树
		node.Left, node.Right = node.Right, node.Left
		// BFS 遍历左子树和右子树
		if node.Left != nil {
			queue.PushBack(node.Left)
		}
		if node.Right != nil {
			queue.PushBack(node.Right)
		}
	}

	return root
}
