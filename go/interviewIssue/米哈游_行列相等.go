package interviewIssue

import (
	"bufio"
	"fmt"
	"os"
)

func EqualRowAndColumn() {
	reader, writer := bufio.NewReaderSize(os.Stdin, 1<<20), bufio.NewWriterSize(os.Stdout, 1<<20)
	defer writer.Flush()

	var n, m int
	fmt.Fscan(reader, &n, &m)
	matrix := make([][]int, n)

	sumRow := make([]int, n)
	sumCol := make([]int, m)

	for i := 0; i < n; i++ {
		matrix[i] = make([]int, m)
		for j := 0; j < m; j++ {
			fmt.Fscan(reader, &matrix[i][j])
			sumRow[i] += matrix[i][j]
			sumCol[j] += matrix[i][j]
		}
	}

	cnt := 0
	for _, currentRowSum := range sumRow {
		for _, currentColSum := range sumCol {
			if currentRowSum == currentColSum {
				cnt++
			}
		}
	}

	fmt.Fprintln(writer, cnt)
}

func EqualRowAndColumnChatGLM_v1() {
	reader := bufio.NewReader(os.Stdin)
	var n, m int
	fmt.Fscan(reader, &n, &m)

	// 存储每行的和
	rowSums := make([]int, n)
	// 存储每列的和
	colSums := make([]int, m)

	// 读取矩阵并计算行和、列和
	for i := 0; i < n; i++ {
		rowSum := 0
		for j := 0; j < m; j++ {
			var val int
			fmt.Fscan(reader, &val)
			rowSum += val
			colSums[j] += val
		}
		rowSums[i] = rowSum
	}

	// 统计列和的频率
	freq := make(map[int]int)
	for _, sum := range colSums {
		freq[sum]++
	}

	// 计算满足条件的行列对数量
	result := 0
	for _, sum := range rowSums {
		result += freq[sum]
	}

	fmt.Println(result)
}
