package linkedlist

/**
 * Definition for singly-linked list.
 * type ListNode struct {
 *     Val int
 *     Next *ListNode
 * }
 */

func locateMiddleNode(head *ListNode) *ListNode {
	// 快慢指针法找到中间节点
	fastPtr, slowPtr := head, head
	for fastPtr != nil && fastPtr.Next != nil {
		fastPtr = fastPtr.Next.Next
		slowPtr = slowPtr.Next
	}

	return slowPtr
}

func isPalindrome(head *ListNode) bool {
	// 构建反转链表
	var reversedHead *ListNode
	iterationPtr := head
	for iterationPtr != nil {
		// 新建节点，头插法构建反转链表
		reversedNext := &ListNode{
			Val:  iterationPtr.Val,
			Next: reversedHead,
		}

		reversedHead = reversedNext
		iterationPtr = iterationPtr.Next
	}

	iterationPtr = head
	reversedIterationPtr := reversedHead
	for iterationPtr != nil {
		if iterationPtr.Val != reversedIterationPtr.Val {
			return false
		}
		iterationPtr, reversedIterationPtr = iterationPtr.Next, reversedIterationPtr.Next
	}

	return true
}
