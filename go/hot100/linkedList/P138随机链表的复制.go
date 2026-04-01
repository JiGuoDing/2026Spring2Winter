package linkedList

type Node struct {
	Val    int
	Next   *Node
	Random *Node
}

func copyRandomList(head *Node) *Node {
	if head == nil {
		return nil
	}

	// 记录该节点是链表中第几个节点
	nodeOrder, newNodeOrder := make(map[*Node]int), make([]*Node, 0)
	// 记录第 m 个节点指向第 n 个节点或空
	direct := make(map[int]int)
	cnt := 0
	curr := head
	for curr != nil {
		nodeOrder[curr] = cnt
		curr = curr.Next
		cnt++
	}

	curr = head
	cnt = 0
	for curr != nil {
		if curr.Random != nil {
			order, _ := nodeOrder[curr.Random]
			direct[cnt] = order
		} else {
			// 标记 Random 为 nil
			direct[cnt] = -1
		}
		// 当前节点指向第 order 个节点
		cnt++
		curr = curr.Next
	}

	curr = head.Next
	// 新头节点
	newHead := &Node{Val: head.Val}
	newNodeOrder = append(newNodeOrder, newHead)
	newCurr := newHead
	// 构建新链表
	for curr != nil {
		newNode := &Node{Val: curr.Val}
		newNodeOrder = append(newNodeOrder, newNode)
		newCurr.Next = newNode
		newCurr = newCurr.Next
		curr = curr.Next
	}

	newCurr = newHead
	curr = head
	cnt = 0
	// 补齐新链表中的 Random
	for curr != nil {
		randomOrder, _ := direct[cnt]
		var random *Node
		if randomOrder != -1 {
			random = newNodeOrder[randomOrder]
		}
		newCurr.Random = random
		newCurr = newCurr.Next
		curr = curr.Next
		cnt++
	}

	return newHead
}

func copyRandomListWeakImproved(head *Node) *Node {
	if head == nil {
		return nil
	}

	// 第一趟：建立原节点到索引的映射，同时统计节点数
	oldToIdx := make(map[*Node]int)
	n := 0
	for curr := head; curr != nil; curr = curr.Next {
		oldToIdx[curr] = n
		n++
	}

	// 第二趟：创建所有新节点，同时记录 Random 指向的索引
	// idxToNew[i] 表示第 i 个节点的新节点
	idxToNew := make([]*Node, n)
	// randomTarget[i] 表示第 i 个新节点的 Random 应该指向的索引，-1 表示 nil
	randomTarget := make([]int, n)

	curr := head
	for i := 0; i < n; i++ {
		// 创建新节点（Next 和 Random 暂时为 nil）
		idxToNew[i] = &Node{Val: curr.Val}

		// 记录 Random 目标
		if curr.Random != nil {
			randomTarget[i] = oldToIdx[curr.Random]
		} else {
			randomTarget[i] = -1
		}

		curr = curr.Next
	}

	// 第三趟：连接 Next 和 Random
	for i := 0; i < n; i++ {
		// 连接 Next
		if i < n-1 {
			idxToNew[i].Next = idxToNew[i+1]
		}

		// 连接 Random
		if randomTarget[i] != -1 {
			idxToNew[i].Random = idxToNew[randomTarget[i]]
		}
		// 否则 Random 保持 nil
	}

	return idxToNew[0]
}

// * 链表穿插法
func copyRandomListImproved(head *Node) *Node {
	if head == nil {
		return nil
	}

	// 第一步：原节点后插入复制节点
	// A -> B -> C  变成  A -> A' -> B -> B' -> C -> C'
	for curr := head; curr != nil; {
		next := curr.Next
		copy := &Node{Val: curr.Val, Next: next}
		curr.Next = copy
		curr = next
	}

	// 第二步：设置复制节点的 Random
	// 原节点的 Random.Next 就是对应复制节点
	for curr := head; curr != nil; curr = curr.Next.Next {
		if curr.Random != nil {
			curr.Next.Random = curr.Random.Next
		}
	}

	// 第三步：拆分链表
	newHead := head.Next
	for curr := head; curr != nil; {
		copy := curr.Next
		nextOld := copy.Next

		// 恢复原链表
		curr.Next = nextOld

		// 连接新链表
		if nextOld != nil {
			copy.Next = nextOld.Next
		}

		curr = nextOld
	}

	return newHead
}
