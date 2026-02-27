package src

import "fmt"

// 返回数组 nums 中第 k 小的元素
func quickSelect(nums []int, k int) int {
	l, r := 0, len(nums)-1
	for {
		// 当区间只剩一个元素时，该元素就是答案
		if l == r {
			return nums[l]
		}

		// 三数取中选 pivot，降低退化概率
		// 选取 nums[l], nums[m], nums[r] 中的中位数作为 pivot
		m := (l + r) >> 1
		if nums[l] > nums[m] {
			nums[l], nums[m] = nums[m], nums[l]
		}
		if nums[l] > nums[r] {
			nums[l], nums[r] = nums[r], nums[l]
		}
		if nums[m] > nums[r] {
			nums[m], nums[r] = nums[r], nums[m]
		}
		pivot := nums[m]

		// Hoare 风格的双指针 partition
		i, j := l, r
		for i <= j {
			// i 向右找 >= pivot 的元素
			for nums[i] < pivot {
				i++
			}
			// j 向左找 <= pivot 的元素
			for nums[j] > pivot {
				j--
			}
			// 交换，使得左侧尽量 <= pivot，右侧尽量 >= pivot
			if i <= j {
				nums[i], nums[j] = nums[j], nums[i]
				i++
				j--
			}
		}

		// 现在 [l..j] <= pivot，[i..r] >= pivot
		// 中间的 (j, i) 区间是 == pivot
		if k <= j {
			// 第 k 小在左边
			r = j
		} else if k >= i {
			// 第 k 小在右边
			l = i
		} else {
			// k 落在中间等于 pivot 的那一段，pivot 就是答案
			return pivot
		}
	}
}

func P1923() {
	var n, k int
	fmt.Scanf("%d %d", &n, &k)

	nums := make([]int, n)
	for i := 0; i < n; i++ {
		fmt.Scanf("%d", &nums[i])
	}

	fmt.Println(quickSelect(nums, k))
}
