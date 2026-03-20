package linkedList

func reverseList(head *ListNode) *ListNode {
	// 递归解法
	if head == nil {
		return head
	}
	if head.Next == nil {
		return head
	}

	next := reverseList(head.Next)
	head.Next.Next = head
	// 这里是为了让头节点的 Next 变为 nil
	head.Next = nil

	return next

	// // 迭代解法
	// var prev *ListNode
	// curr := head
	// for curr != nil {
	//     next := curr.Next
	//     curr.Next = prev
	//     prev = curr
	//     curr = next
	// }

	// return prev
}
