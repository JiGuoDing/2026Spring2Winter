package src

import (
	"bufio"
	"math/rand"
	"os"
	"strconv"
)

const INSERT_SORT_THRESHOLD = 16

// 插入排序（用于小规模子数组）
func insertionSort(a []int, l, r int) {
	for i := l + 1; i <= r; i++ {
		pivot := a[i]
		j := i - 1
		for j >= l && a[j] > pivot {
			// 比 pivot 大的元素右移
			a[j+1] = a[j]
			j--
		}
		// a[j] <= pivot 或 j < l，此时 pivot 应插入到 j+1 位置
		a[j+1] = pivot
	}
}

// 三路快排（原地实现，Dijkstra 三向切分）
func threeWayQuickSort(a []int, l, r int) {
	for l < r {
		// 当子数组长度 <= 16 时，不再进行递归快排，而是直接用插入排序
		if r-l+1 <= INSERT_SORT_THRESHOLD {
			insertionSort(a, l, r)
			return
		}

		// 随机选择 pivot 并交换到开头（可选，也可直接用 a[l]）
		pivotIndex := l + rand.Intn(r-l+1)
		a[l], a[pivotIndex] = a[pivotIndex], a[l]
		pivot := a[l]

		// 三路划分：[l+1, lt) < pivot, [lt, gt] == pivot, (gt, r] > pivot
		lt := l + 1 // 小于区域的右边界 (下一个 < pivot 的元素应该放在 lt 位置)
		gt := r     // 大于区域的左边界 (下一个 > pivot 的元素应该放在 gt 位置)
		i := l + 1  // 当前正在检查的元素

		for i <= gt {
			if a[i] < pivot {
				// a[i] < pivot，交换到小于区域
				a[lt], a[i] = a[i], a[lt]
				lt++
				i++
			} else if a[i] > pivot {
				// a[i] > pivot，交换到大于区域
				a[i], a[gt] = a[gt], a[i]
				// 注意：这里 i 不++，因为换来的元素需要再检查一次
				gt--
			} else {
				// a[i] == pivot，直接跳过
				i++
			}
		}

		// 将 pivot 放到等于区域的起始位置
		a[l], a[lt-1] = a[lt-1], a[l]

		// 此时：
		// [l, lt-2] < pivot
		// [lt-1, gt] == pivot
		// [gt+1, r] > pivot

		leftLen := (lt - 1) - l
		rightLen := r - gt

		// 尾递归优化：先递归处理较小的一侧，另一侧用循环迭代
		if leftLen < rightLen {
			threeWayQuickSort(a, l, lt-2)
			l = gt + 1
		} else {
			threeWayQuickSort(a, gt+1, r)
			r = lt - 2
		}
	}
}

func P1177() {
	in := bufio.NewScanner(os.Stdin)
	in.Split(bufio.ScanWords)
	out := bufio.NewWriter(os.Stdout)
	defer out.Flush()

	in.Scan()
	n, _ := strconv.Atoi(in.Text())
	a := make([]int, n)
	for i := range n {
		in.Scan()
		a[i], _ = strconv.Atoi(in.Text())
	}

	threeWayQuickSort(a, 0, n-1)

	for i, x := range a {
		out.WriteString(strconv.Itoa(x))
		if i < n-1 {
			out.WriteByte(' ')
		}
	}
	out.WriteByte('\n')
}
