package linkedList

// sortList 对链表进行升序排序，使用归并排序算法
func sortList(head *ListNode) *ListNode {
	if head == nil || head.Next == nil {
		return head
	}

	// 使用快慢指针找到链表中点，将链表分为两半
	// slow 最终指向中点或左中点，fast 用于定位终点
	slow, fast := head, head.Next
	for fast != nil && fast.Next != nil {
		slow = slow.Next
		fast = fast.Next.Next
	}
	// 此时 slow 是中点，将链表从中间断开
	// mid 是右半部分的头节点
	mid := slow.Next
	// 断开链表，左半部分结束于 slow
	slow.Next = nil

	// 递归排序左右两部分
	left := sortList(head)
	right := sortList(mid)

	return merge(left, right)

}

// 合并两个有序链表，返回合并后的头节点
func merge(list1, list2 *ListNode) *ListNode {
	// 创建虚拟头节点，避免处理空指针的特殊情况
	dummy := &ListNode{}
	tail := dummy

	for list1 != nil && list2 != nil {
		if list1.Val < list2.Val {
			tail.Next = list1
			list1 = list1.Next
		} else {
			tail.Next = list2
			list2 = list2.Next
		}
		// 移动 tail 指针
		tail = tail.Next
	}

	if list1 != nil {
		tail.Next = list1
	} else {
		tail.Next = list2
	}

	return dummy.Next
}
