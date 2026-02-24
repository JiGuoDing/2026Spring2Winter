package src

import "fmt"

func P2241() {
	var n, m int
	fmt.Scan(&n, &m)

	// 总矩形数 (公式)
	totalRect := n * (n + 1) / 2 * m * (m + 1) / 2

	// 正方形数
	squareCount := 0
	minSide := min(m, n)
	for k := 1; k <= minSide; k++ {
		squareCount += (n - k + 1) * (m - k + 1)
	}

	rectangleCount := totalRect - squareCount

	fmt.Printf("%d %d\n", squareCount, rectangleCount)
}
