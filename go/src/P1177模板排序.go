package src

import "fmt"

func quickSort(arr []int, left, right int) {
	if left >= right {
		return
	}

	i, j := left, right
	// 基准值 (此处是取左端元素)
	x := arr[left]

	for i < j {
		// 从右向左找第一个 < x 的元素
		for i < j && arr[j] >= x {
			j--
		}
		if i < j {
			arr[i] = arr[j]
			i++
		}

		// 从左向右找第一个 > x 的元素
		for i < j && arr[i] <= x {
			i++
		}
		if i < j {
			arr[j] = arr[i]
			j--
		}

		// 将基准值填入最终位置
		if i >= j {
			arr[i] = x
		}
	}

	quickSort(arr, left, j-1)
	quickSort(arr, j+1, right)
}

func P1177() {
	var n int
	fmt.Scan(&n)

	original := make([]int, n)
	for i := 0; i < n; i++ {
		fmt.Scan(&original[i])
	}

	sorted := make([]int, n)
	copy(sorted, original)
	quickSort(sorted, 0, n-1)

	for i := 0; i < n; i++ {
		fmt.Printf("%d ", sorted[i])
	}
}
