package linkedList

func mergeTwoLists(list1 *ListNode, list2 *ListNode) *ListNode {
	// 处理边界情况
	if list1 == nil {
		return list2
	} else if list2 == nil {
		return list1
	}

	// 虚拟头节点
	head := &ListNode{Val: -1}
	newList := head

	for list1 != nil && list2 != nil {
		// 两个链表都没到末尾，取其中大的
		if list1.Val > list2.Val {
			newList.Next = list2
			list2 = list2.Next
		} else {
			newList.Next = list1
			list1 = list1.Next
		}
		newList = newList.Next
	}

	if list1 != nil {
		newList.Next = list1
	} else {
		newList.Next = list2
	}
	return head.Next
}
