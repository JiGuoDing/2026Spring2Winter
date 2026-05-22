package interviewIssue

import "fmt"

type ListNode struct {
	Val  int
	Next *ListNode
}

// 反转一个链表
func reverseList(head *ListNode) *ListNode {
	var prev *ListNode
	curr := head
	for curr != nil {
		next := curr.Next
		curr.Next = prev
		prev = curr
		curr = next
	}
	return prev
}

func addTwoReversedLists(head1, head2 *ListNode) *ListNode {
	if head1 == nil {
		return head2
	}
	if head2 == nil {
		return head1
	}

	dummy := &ListNode{}
	// ! 不能写成 var dummy *ListNode
	curr := dummy
	carry := 0
	for head1 != nil || head2 != nil {
		val1, val2 := 0, 0
		if head1 != nil {
			val1 = head1.Val
			head1 = head1.Next
		}
		if head2 != nil {
			val2 = head2.Val
			head2 = head2.Next
		}
		newVal := (val1+val2)%10 + carry
		carry = (val1 + val2) / 10

		newNode := &ListNode{
			Val: newVal,
		}
		curr.Next = newNode
		curr = curr.Next
	}

	return dummy.Next
}

func AddTwoLists(head1, head2 *ListNode) *ListNode {
	reversedHead1 := reverseList(head1)
	reversedHead2 := reverseList(head2)
	newReversedHead := addTwoReversedLists(reversedHead1, reversedHead2)
	newHead := reverseList(newReversedHead)
	return newHead
}

func TestAddTwoLists() {
	node1 := &ListNode{Val: 7}
	node2 := &ListNode{Val: 0}
	node1.Next = node2
	node3 := &ListNode{Val: 4}
	node2.Next = node3
	node4 := &ListNode{Val: 8}
	node3.Next = node4

	node5 := &ListNode{Val: 5}
	node6 := &ListNode{Val: 6}
	node5.Next = node6
	node7 := &ListNode{Val: 2}
	node6.Next = node7

	addedNodeList := AddTwoLists(node1, node5)
	for node := addedNodeList; node != nil; node = node.Next {
		fmt.Println(node.Val)
	}
}
