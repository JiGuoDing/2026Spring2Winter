package heap

// ========================================================
// 方法一：最小堆法
// 维护一个大小为 k 的最小堆
// 堆顶 = 第 k 大的元素
// ========================================================

// MinHeap 最小堆结构体
type MinHeap struct {
	data []int
	size int
}

// NewMinHeap 创建一个空的最小堆
func NewMinHeap() *MinHeap {
	return &MinHeap{data: []int{}, size: 0}
}

// Len 返回堆的大小
func (h *MinHeap) Len() int {
	return h.size
}

// Top 返回堆顶元素（最小值），不删除
func (h *MinHeap) Top() int {
	return h.data[0]
}

// Push 向堆中插入元素
// 步骤：追加到末尾 -> 上浮到合适位置
func (h *MinHeap) Push(val int) {
	h.data = append(h.data, val)
	h.size++
	h.siftUp(h.size - 1) // 对最后一个元素执行上浮
}

// Pop 移除并返回堆顶元素（最小值）
// 步骤：记录堆顶 -> 末尾元素移到堆顶 -> 下沉到合适位置
func (h *MinHeap) Pop() int {
	top := h.data[0]
	h.size--
	if h.size > 0 {
		// 将最后一个元素移到堆顶
		h.data[0] = h.data[h.size]
		h.data = h.data[:h.size]
		h.siftDown(0) // 对堆顶元素执行下沉
	} else {
		h.data = h.data[:0]
	}
	return top
}

// siftUp 上浮操作：将索引 i 处的元素向上移动到正确位置
// 当前节点 < 父节点 时，交换（维护最小堆性质）
//
//	    1
//	   / \
//	  3   2
//	 /
//	0  <- 插入了 0，需要上浮
//
// 上浮过程：0<3 交换 -> 0<1 交换 -> 到达根节点，停止
func (h *MinHeap) siftUp(i int) {
	for i > 0 {
		parent := (i - 1) / 2 // 父节点索引
		if h.data[i] < h.data[parent] {
			// 当前节点比父节点小，交换
			h.data[i], h.data[parent] = h.data[parent], h.data[i]
			i = parent // 继续向上检查
		} else {
			break // 已满足堆性质，停止
		}
	}
}

// siftDown 下沉操作：将索引 i 处的元素向下移动到正确位置
// 当前节点 > 子节点中的最小值 时，交换（维护最小堆性质）
//
//	    9           <- 堆顶被替换为 9，需要下沉
//	   / \
//	  3   2
//	 / \
//	5   4
//
// 下沉过程：9>min(3,2)=2，与2交换 -> 9>min(?,?)...直到叶子
func (h *MinHeap) siftDown(i int) {
	for {
		smallest := i    // 假设当前节点最小
		left := 2*i + 1  // 左子节点索引
		right := 2*i + 2 // 右子节点索引

		// 找左、右、当前 三者中的最小值
		if left < h.size && h.data[left] < h.data[smallest] {
			smallest = left
		}
		if right < h.size && h.data[right] < h.data[smallest] {
			smallest = right
		}

		if smallest == i {
			break // 当前节点已是最小，停止下沉
		}

		// 与最小子节点交换
		h.data[i], h.data[smallest] = h.data[smallest], h.data[i]
		i = smallest // 继续向下检查
	}
}

// findKthLargestByHeap 使用最小堆找第 k 大元素
//
// 核心思想：
//
//	维护一个大小为 k 的最小堆
//	- 堆中始终保存"目前遇到的最大的 k 个数"
//	- 堆顶 = 这 k 个数中最小的 = 第 k 大的数
//
// 过程示例（k=3，nums=[3,2,1,5,6,4]）：
//
//	插入 3       -> 堆:[3]
//	插入 2       -> 堆:[2,3]
//	插入 1       -> 堆:[1,3,2]   堆满了
//	插入 5 > 堆顶1 -> 弹出1，插入5 -> 堆:[2,3,5]
//	插入 6 > 堆顶2 -> 弹出2，插入6 -> 堆:[3,5,6]
//	插入 4 > 堆顶3 -> 弹出3，插入4 -> 堆:[4,5,6]
//	最终堆顶 = 4 = 第3大元素 ✓
func findKthLargest(nums []int, k int) int {
	heap := NewMinHeap()

	for _, num := range nums {
		if heap.Len() < k {
			// 堆未满，直接插入
			heap.Push(num)
		} else if num > heap.Top() {
			// 堆已满，当前元素比堆顶大
			// 说明当前元素可以进入"前k大"，弹出最小的，插入当前
			heap.Pop()
			heap.Push(num)
		}
		// 若 num <= 堆顶，说明不在前k大中，忽略
	}

	return heap.Top() // 堆顶即第 k 大元素
}

// ========================================================
// 方法二：快速选择法（QuickSelect）
// 基于快速排序的 partition 思想
// ========================================================

// findKthLargestByQuickSelect 使用快速选择找第 k 大元素
//
// 核心思想：
//
//	第 k 大 = 排序后索引为 n-k 的元素（从小到大）
//	每次 partition 后，pivot 落在最终位置 p：
//	  - 若 p == target，找到答案
//	  - 若 p < target，在右半部分继续找
//	  - 若 p > target，在左半部分继续找
func findKthLargestByQuickSelect(nums []int, k int) int {
	n := len(nums)
	target := n - k // 转化为：找第 target 小（从0开始的索引）
	return quickSelect(nums, 0, n-1, target)
}

// quickSelect 在 nums[left..right] 中找索引为 target 的元素
func quickSelect(nums []int, left, right, target int) int {
	if left == right {
		return nums[left]
	}

	// 执行 partition，返回 pivot 的最终位置
	pivotIdx := partition(nums, left, right)

	if pivotIdx == target {
		return nums[pivotIdx] // 恰好找到
	} else if pivotIdx < target {
		return quickSelect(nums, pivotIdx+1, right, target) // 在右边找
	} else {
		return quickSelect(nums, left, pivotIdx-1, target) // 在左边找
	}
}

// partition 分区操作
// 选取最右元素为 pivot，将数组分为两部分：
//
//	[left .. p-1] <= pivot   [p] = pivot   [p+1 .. right] >= pivot
//
// 过程示例（nums=[3,2,1,5,6,4], left=0, right=5）：
//
//	pivot = 4, i = -1（i 指向"已找到的小于等于pivot区域"的末尾）
//	j=0: nums[0]=3 <= 4, i=0, swap(0,0) -> [3,2,1,5,6,4]
//	j=1: nums[1]=2 <= 4, i=1, swap(1,1) -> [3,2,1,5,6,4]
//	j=2: nums[2]=1 <= 4, i=2, swap(2,2) -> [3,2,1,5,6,4]
//	j=3: nums[3]=5 >  4, 跳过
//	j=4: nums[4]=6 >  4, 跳过
//	最后 swap(i+1=3, right=5) -> [3,2,1,4,6,5]
//	返回 p=3，nums[3]=4 在最终位置
func partition(nums []int, left, right int) int {
	pivot := nums[right] // 选最右元素为基准
	i := left - 1        // i 指向"小于等于pivot区"的末尾

	for j := left; j < right; j++ {
		if nums[j] <= pivot {
			i++
			nums[i], nums[j] = nums[j], nums[i] // 将小元素移到左边
		}
	}

	// 将 pivot 放到正确位置
	nums[i+1], nums[right] = nums[right], nums[i+1]
	return i + 1 // 返回 pivot 的最终索引
}
