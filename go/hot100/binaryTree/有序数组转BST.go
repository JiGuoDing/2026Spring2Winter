package binaryTree

// sortedArrayToBST 将有序数组转换为高度平衡的二叉搜索树
// 时间复杂度：O(n)，每个元素访问一次
// 空间复杂度：O(log n)，递归栈的深度
func sortedArrayToBST(nums []int) *TreeNode {
	if len(nums) == 0 {
		return nil
	}

	return buildBST(nums, 0, len(nums)-1)
}

// buildBST 递归构建 BST
func buildBST(nums []int, left, right int) *TreeNode {
	// 递归终止条件
	if left > right {
		return nil
	}

	// 选择中间位置作为根节点
	// 使用 left + (right-left)/2 防止溢出
	mid := left + (right-left)/2

	// 构建根节点
	root := &TreeNode{Val: nums[mid]}

	// 递归构建左右子树
	root.Left = buildBST(nums, left, mid-1)
	root.Right = buildBST(nums, mid+1, right)

	return root
}

// sortedArrayToBSTParallel 并发版本 - 使用 Goroutine 并行构建左右子树
// 适用于非常大的数组，利用多核 CPU 加速构建过程
// 时间复杂度：O(n/log n) 理想情况下（p 个处理器）
// 空间复杂度：O(log n) - 递归栈深度
func sortedArrayToBSTParallel(nums []int) *TreeNode {
	if len(nums) == 0 {
		return nil
	}

	// 使用 channel 接收结果
	resultChan := make(chan *TreeNode, 1)
	buildBSTParallel(nums, 0, len(nums)-1, resultChan)
	return <-resultChan
}

// buildBSTParallel 并发构建 BST
// 当区间足够大时，使用 goroutine 并行构建左右子树
func buildBSTParallel(nums []int, left, right int, resultChan chan<- *TreeNode) {
	if left > right {
		resultChan <- nil
		return
	}

	mid := left + (right-left)/2
	root := &TreeNode{Val: nums[mid]}

	// 阈值：当区间长度小于此值时，不再并行（避免 goroutine 开销过大）
	const threshold = 1000

	if right-left > threshold {
		// 并行构建左右子树
		leftChan := make(chan *TreeNode, 1)
		rightChan := make(chan *TreeNode, 1)

		go buildBSTParallel(nums, left, mid-1, leftChan)
		go buildBSTParallel(nums, mid+1, right, rightChan)

		// 等待两个子树构建完成
		root.Left = <-leftChan
		root.Right = <-rightChan
	} else {
		// 串行构建（小区间不需要并行）
		root.Left = buildBST(nums, left, mid-1)
		root.Right = buildBST(nums, mid+1, right)
	}

	resultChan <- root
}

// sortedArrayToBSTParallelWithPool 带协程池的并发版本
// 限制最大并发数，避免创建过多 goroutine
// 适用于超大数组（百万级元素）
func sortedArrayToBSTParallelWithPool(nums []int) *TreeNode {
	if len(nums) == 0 {
		return nil
	}

	// 根据 CPU 核心数设置并发度
	maxWorkers := 4 // 可以根据 runtime.NumCPU() 调整

	resultChan := make(chan *TreeNode, 1)
	semaphore := make(chan struct{}, maxWorkers)

	buildBSTParallelWithPool(nums, 0, len(nums)-1, resultChan, semaphore)
	return <-resultChan
}

// buildBSTParallelWithPool 使用信号量控制并发的构建函数
func buildBSTParallelWithPool(nums []int, left, right int, resultChan chan<- *TreeNode, semaphore chan struct{}) {
	if left > right {
		resultChan <- nil
		return
	}

	mid := left + (right-left)/2
	root := &TreeNode{Val: nums[mid]}

	const threshold = 1000

	if right-left > threshold {
		// 获取信号量（如果满了会阻塞）
		select {
		case semaphore <- struct{}{}:
			// 成功获取，可以创建 goroutine
			leftChan := make(chan *TreeNode, 1)
			rightChan := make(chan *TreeNode, 1)

			go func() {
				buildBSTParallelWithPool(nums, left, mid-1, leftChan, semaphore)
			}()
			go func() {
				buildBSTParallelWithPool(nums, mid+1, right, rightChan, semaphore)
			}()

			root.Left = <-leftChan
			root.Right = <-rightChan

			// 释放信号量
			<-semaphore
		default:
			// 无法获取信号量，降级为串行
			root.Left = buildBST(nums, left, mid-1)
			root.Right = buildBST(nums, mid+1, right)
		}
	} else {
		// 小区间直接串行
		root.Left = buildBST(nums, left, mid-1)
		root.Right = buildBST(nums, mid+1, right)
	}

	resultChan <- root
}
