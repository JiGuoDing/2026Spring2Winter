package linkedList

// 使用 set 记录已经出现的节点地址，当再次遇到已经出现过的节点时，说明出现了环
func detectCycle(head *ListNode) *ListNode {
	if head == nil || head.Next == nil {
		return nil
	}

	nodeSet := make(map[*ListNode]struct{})

	pseudoHead := head
	for pseudoHead != nil {
		if _, ok := nodeSet[pseudoHead]; ok {
			// 说明有环，直接返回这个节点
			return pseudoHead
		} else {
			// 还没遇到环，加入 set
			nodeSet[pseudoHead] = struct{}{}
			pseudoHead = pseudoHead.Next
		}
	}

	return nil
}

// 使用快慢指针检测环
// 1. 判断是否有环：快指针每次走两步，慢指针每次走一步。如果相遇，则有环。
// 2. 寻找入环点：相遇后，将一个指针重置到头节点，两个指针每次都走一步，再次相遇的点即为入环点。
func detectCycleFastSlow(head *ListNode) *ListNode {
	if head == nil || head.Next == nil {
		return nil
	}

	slow, fast := head, head

	// 第一步，寻找环
	for fast != nil && fast.Next != nil {
		slow = slow.Next
		fast = fast.Next.Next
		if fast == slow {
			break
		}
	}

	// 如果 fast 到头了，说明没环
	if fast == nil || fast.Next == nil {
		return nil
	}

	// 第二步：寻找入环点
	slow = head
	for slow != fast {
		slow = slow.Next
		fast = fast.Next
	}

	return slow

}
