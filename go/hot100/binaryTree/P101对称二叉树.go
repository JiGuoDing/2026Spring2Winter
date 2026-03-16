package binaryTree

import "container/list"

func isSymmetricDFS(root *TreeNode) bool {
	// 处理边界情况
	if root == nil {
		return true
	}

	return check(root.Left, root.Right)
}

func check(left, right *TreeNode) bool {
	if left == nil && right == nil {
		return true
	}
	if left == nil || right == nil {
		return false
	}
	if left.Val != right.Val {
		return false
	}
	return check(left.Left, right.Right) && check(left.Right, right.Left)
}

// key insight: 对称的继承性，两个对称的节点，其一左子树与另一右子树对称，反之亦然
func isSymmetricBFS(root *TreeNode) bool {
	if root == nil {
		return true
	}

	queue := list.New()
	// 核心技巧：将根节点的左右孩子成对放入队列
	// 即使孩子是 nil 也要放入，以便检测结构不对称
	queue.PushBack(root.Left)
	queue.PushBack(root.Right)

	for queue.Len() > 0 && queue.Len() >= 2 {
		// 每次取出两个节点进行比较
		e1 := queue.Front()
		queue.Remove(e1)
		node1 := e1.Value // 可能是 *TreeNode 或 nil

		e2 := queue.Front()
		queue.Remove(e2)
		node2 := e2.Value // 可能是 *TreeNode 或 nil

		// 情况1: 两个都是 nil，对称，继续
		if node1 == nil && node2 == nil {
			continue
		}

		// 情况2: 一个是 nil，另一个不是，不对称
		if node1 == nil || node2 == nil {
			return false
		}

		// 情况3: 两个都不是 nil，比较值
		n1 := node1.(*TreeNode)
		n2 := node2.(*TreeNode)
		if n1.Val != n2.Val {
			return false
		}

		// 关键：下一层的入队顺序必须是“交叉”的
		// 比较 n1.Left 和 n2.Right
		queue.PushBack(n1.Left)
		queue.PushBack(n2.Right)

		// 比较 n1.Right 和 n2.Left
		queue.PushBack(n1.Right)
		queue.PushBack(n2.Left)
	}

	return true
}
