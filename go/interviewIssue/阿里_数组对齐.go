package interviewIssue

import (
	"bufio"
	"fmt"
	"os"
)

func AlignArray() {
	reader, writer := bufio.NewReaderSize(os.Stdin, 1<<20), bufio.NewWriterSize(os.Stdout, 1<<20)
	defer writer.Flush()
	var T int
	fmt.Fscan(reader, &T)
	for ; T > 0; T-- {
		var n int
		fmt.Fscan(reader, &n)
		A, B := make([]int, n), make([]int, n)
		for i := 0; i < n; i++ {
			fmt.Fscan(reader, &A[i])
		}
		for i := 0; i < n; i++ {
			fmt.Fscan(reader, &B[i])
		}
		needA, needB := 0, 0
		for i := 0; i < n; i++ {
			if A[i] > B[i] {
				needA += A[i] - B[i]
			} else {
				needB += B[i] - A[i]
			}
		}
		fmt.Fprintln(writer, max(needA, needB))
	}
}

func abs(a, b int) int {
	if a > b {
		return a - b
	} else {
		return b - a
	}
}

func sum(arr []int) int {
	total := 0
	for _, num := range arr {
		total += num
	}
	return total
}
