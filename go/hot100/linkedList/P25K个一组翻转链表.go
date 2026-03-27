package linkedList

// 25. K 个一组翻转链表
// 给你链表的头节点 head ，每 k 个节点一组进行翻转，请你返回修改后的链表。
// k 是一个正整数，它的值小于或等于链表的长度。如果节点总数不是 k 的整数倍，
// 那么请将最后剩余的节点保持原有顺序。
// 你不能只是单纯的改变节点内部的值，而是需要实际进行节点交换。
//
// 示例 1:
// 输入：head = [1,2,3,4,5], k = 2
// 输出：[2,1,4,3,5]
//
// 示例 2:
// 输入：head = [1,2,3,4,5], k = 3
// 输出：[3,2,1,4,5]
//
// 提示:
// 链表中的节点数目为 n
// 1 <= k <= n <= 5000
// 0 <= Node.val <= 1000
//
// 进阶：你可以设计一个只用 O(1) 额外空间的算法解决此问题吗？

// reverseKGroup 主函数：K 个一组翻转链表
func reverseKGroup(head *ListNode, k int) *ListNode {
	// 边界情况：空链表或 k=1 无需翻转
	if head == nil || k == 1 {
		return head
	}

	// 创建虚拟头节点，简化对头节点的处理
	dummy := &ListNode{Next: head}

	// prev 指向待翻转组的前一个节点
	prev := dummy

	for {
		// Step 1: 检查剩余节点是否足够 k 个
		end := prev
		count := 0
		for end.Next != nil && count < k {
			end = end.Next
			count++
		}

		// 如果不足 k 个节点，直接结束（保持原有顺序）
		if count < k {
			break
		}

		// Step 2: 记录关键位置
		groupHead := prev.Next    // 当前组的头节点（翻转后会变成尾）
		nextGroupHead := end.Next // 下一组的头节点

		// Step 3: 断开与下一组的连接（独立出当前组）
		end.Next = nil

		// Step 4: 翻转当前组（使用经典的三指针法）
		// 翻转后：newGroupHead 是新头，groupHead 变成了尾
		newGroupHead := reverseListHelper(groupHead)

		// Step 5: 重新连接
		// prev -> 新头
		// 原头（现在是尾）-> 下一组
		prev.Next = newGroupHead
		groupHead.Next = nextGroupHead

		// Step 6: 移动 prev 到下一组的前面
		// 注意：此时 groupHead 已经是当前组的尾节点了
		prev = groupHead
	}

	return dummy.Next
}

// reverseListHelper 翻转单链表（辅助函数）
// 使用经典的三指针法：prev, curr, next
func reverseListHelper(head *ListNode) *ListNode {
	var prev *ListNode = nil
	curr := head

	for curr != nil {
		next := curr.Next // 先保存下一个节点
		curr.Next = prev  // 反转指针
		prev = curr       // prev 前移
		curr = next       // curr 前移
	}

	return prev // prev 成为新的头节点
}

// ============================================================================
// 【优化版本】一体化实现（避免断开重连，代码更简洁）
// ============================================================================

// reverseKGroupOptimized 优化版本：在组内直接翻转，不需要断开连接
func reverseKGroupOptimized(head *ListNode, k int) *ListNode {
	if head == nil || k == 1 {
		return head
	}

	dummy := &ListNode{Next: head}
	prev := dummy

	for {
		// Step 1: 检查是否有足够的节点
		end := prev
		count := 0
		for end.Next != nil && count < k {
			end = end.Next
			count++
		}

		if count < k {
			break
		}

		// Step 2: 记录关键节点
		curr := prev.Next // 当前组的头

		// Step 3: 在组内进行 k-1 次头插法翻转
		// 示例：1->2->3->4, k=3
		// 第一次：2->1, 3->2->1, 剩下 4
		// 第二次：3->2->1, 4->3->2->1
		for i := 0; i < k-1; i++ {
			next := curr.Next     // 保存当前节点的下一个
			curr.Next = next.Next // 跳过 next 节点
			next.Next = prev.Next // next 插入到组首
			prev.Next = next      // 更新组首
			// curr 保持不动，继续处理下一个节点
		}

		// Step 4: 移动 prev 到下一组
		// 此时 curr 是当前组的尾节点
		prev = curr
	}

	return dummy.Next
}

// ============================================================================
// 【图解说明】
// ============================================================================
//
// 示例：head = [1,2,3,4,5], k = 3
//
// 初始状态:
// dummy -> 1 -> 2 -> 3 -> 4 -> 5
// prev↑
//
// 第一组翻转前:
// prev=dummy, groupHead=1, end=3, nextGroupHead=4
//
// 第一组翻转后 (reverseList):
// dummy -> 3 -> 2 -> 1 -> 4 -> 5
//                prev↑ (准备处理下一组)
//
// 第二组检查:
// 从 prev(节点 1) 开始数，只有 4->5，不足 3 个，结束
//
// 最终结果：[3,2,1,4,5]
//
// 【复杂度分析】
// 时间复杂度：O(n)，其中 n 是链表长度。需要遍历链表常数次
// 空间复杂度：O(1)，只使用了常数个额外变量
//
// 【关键点总结】
// 1. 使用虚拟头节点简化边界处理
// 2. 每次先检查剩余节点是否足够 k 个
// 3. 不足 k 个时保持原有顺序（这是题目的特殊要求）
// 4. 翻转后要正确连接前后两组
// 5. prev 指针要移动到正确位置（当前组的尾节点）
