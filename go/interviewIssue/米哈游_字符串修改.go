package interviewIssue

import (
	"bufio"
	"fmt"
	"os"
)

func replaceString() {
	reader := bufio.NewReaderSize(os.Stdin, 1<<20)
	writer := bufio.NewWriterSize(os.Stdout, 1<<20)
	defer writer.Flush()

	var n int
	fmt.Fscan(reader, &n)
	A := make([]int, n+1)
	for i := 1; i <= n; i++ {
		fmt.Fscan(reader, &A[i])
	}

	if n == 1 {
		fmt.Fprintln(writer, 0)
		return
	}

	up := make([]int, n+1)
	down := make([]int, n+1)
	up[1] = 1
	down[1] = 1

	for i := 2; i <= n; i++ {
		if A[i] > A[i-1] {
			up[i] = down[i-1] + 1
			down[i] = down[i-1]
		} else if A[i] < A[i-1] {
			down[i] = up[i-1] + 1
			up[i] = up[i-1]
		} else {
			up[i] = up[i-1]
			down[i] = down[i-1]
		}
	}

	maxLen := max(up[n], down[n])
	fmt.Fprintln(writer, n-maxLen)
}
