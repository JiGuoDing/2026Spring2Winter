package linkedlist

/**
 * Definition for singly-linked list.
 * type ListNode struct {
 *     Val int
 *     Next *ListNode
 * }
 */
func hasCycle(head *ListNode) bool {
	// 用 set 记录已经出现的节点地址
	// set := make(map[*ListNode]struct{})

	// for head != nil {
	// 如果当前遍历到的地址已经在 set 出现过，说明出现了环
	//     if _, ok := set[head]; ok {
	//         return true
	//     } else {
	//         set[head] = struct{}{}
	//     }

	//     head = head.Next
	// }
	// return false

	// 快慢指针
	fast, slow := head, head
	for fast != nil && fast.Next != nil {
		fast = fast.Next.Next
		slow = slow.Next
		if fast == slow {
			return true
		}
	}
	return false
}
