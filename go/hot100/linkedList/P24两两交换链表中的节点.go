package linkedList

func swapPairs(head *ListNode) *ListNode {
	// 处理边界情况
	if head == nil || head.Next == nil {
		return head
	}

	// 虚拟头节点
	dummy := &ListNode{Next: head}
	// 分别只想要交换的两个节点
	prev, first, second := dummy, dummy.Next, dummy.Next.Next

	for second != nil {
		// 交换相邻两个节点
		prev.Next = second
		first.Next = second.Next
		second.Next = first

		if first.Next == nil || first.Next.Next == nil {
			break
		}

		prev = first
		first = prev.Next
		second = first.Next
	}

	return dummy.Next
}

// 优化版本：更清晰的指针操作和循环控制
func swapPairsOptimized(head *ListNode) *ListNode {
	// 边界情况：空链表或只有一个节点，无需交换
	if head == nil || head.Next == nil {
		return head
	}

	// 创建虚拟头节点，简化对头节点的处理
	dummy := &ListNode{Next: head}

	// current 指向待交换的两个节点的前一个节点
	current := dummy

	// 当 current 后面至少有两个节点时，继续交换
	for current.Next != nil && current.Next.Next != nil {
		// 标记待交换的两个节点
		first := current.Next       // 第一个节点
		second := current.Next.Next // 第二个节点

		// 【关键步骤】交换两个节点（三步操作）
		// 1. current 指向 second（改变前驱节点的指向）
		current.Next = second
		// 2. first 指向 second 的下一个节点（断开 first 和 second 的连接）
		first.Next = second.Next
		// 3. second 指向 first（完成交换）
		second.Next = first

		// 【移动指针】准备下一轮交换
		// current 移动到 first（此时 first 已经在 second 后面了）
		// 注意：不能移动到 second，因为 first 现在是这一对的第二个节点
		current = first
	}

	return dummy.Next
}
