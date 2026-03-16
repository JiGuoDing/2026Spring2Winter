package binaryTree

import "container/list"

func levelOrderList(root *TreeNode) [][]int {
	if root == nil {
		return nil
	}

	var result [][]int

	// 需要一层一层地添加节点，然后一层一层地遍历
	queue := list.New()
	queue.PushBack(root)
	// 暂存下一层的节点
	nodeStorage := []*TreeNode{}

	// 每一层的节点值
	var tempRes []int

	for queue.Len() > 0 {
		node := queue.Front().Value.(*TreeNode)
		queue.Remove(queue.Front())
		tempRes = append(tempRes, node.Val)

		if node.Left != nil {
			nodeStorage = append(nodeStorage, node.Left)
		}
		if node.Right != nil {
			nodeStorage = append(nodeStorage, node.Right)
		}

		if queue.Len() == 0 {
			for _, n := range nodeStorage {
				queue.PushBack(n)
			}
			// 清空暂存节点
			nodeStorage = []*TreeNode{}
			result = append(result, tempRes)
			tempRes = []int{}
		}
	}

	return result
}

func levelOrder(root *TreeNode) [][]int {
	if root == nil {
		return nil
	}

	var result [][]int

	// 使用切片模拟队列
	queue := []*TreeNode{root}
	// 暂存下一层的节点
	nodeStorage := []*TreeNode{}
	// 每一层的节点值
	var tempRes []int

	for len(queue) > 0 {
		// 出队，取出第一个元素
		node := queue[0]
		// 出队：切片向后移动一位，相当于移出头部
		queue = queue[1:]

		tempRes = append(tempRes, node.Val)

		if node.Left != nil {
			nodeStorage = append(nodeStorage, node.Left)
		}
		if node.Right != nil {
			nodeStorage = append(nodeStorage, node.Right)
		}

		// 如果当前层处理完毕（队列空了）
		if len(queue) == 0 {
			// 将暂存的下一层节点全部加入队列
			queue = append(queue, nodeStorage...)

			// 重置暂存切片（重要：重新分配一个底层数组，避免引用问题）
			nodeStorage = []*TreeNode{}

			// 保存当前层结果
			result = append(result, tempRes)

			// 重置当前层结果切片
			tempRes = []int{}
		}
	}

	return result
}
