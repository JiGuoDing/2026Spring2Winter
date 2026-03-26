package linkedList

// 快慢指针
func removeNthFromEnd(head *ListNode, n int) *ListNode {
	dummy := &ListNode{Next: head}
	fast, slow := dummy, dummy

	// 快指针先走 n 步
	for i := 0; i <= n; i++ {
		fast = fast.Next
	}

	// 快慢指针一起走
	for fast != nil {
		fast = fast.Next
		slow = slow.Next
	}

	// 删除目标节点
	slow.Next = slow.Next.Next

	return dummy.Next
}
