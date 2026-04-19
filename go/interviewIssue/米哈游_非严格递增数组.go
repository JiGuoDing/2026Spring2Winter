package interviewIssue

import (
	"bufio"
	"fmt"
	"os"
)

func NonStrictlyIncreasingArray() {
	reader, writer := bufio.NewReaderSize(os.Stdin, 1<<20), bufio.NewWriterSize(os.Stdout, 1<<20)
	defer writer.Flush()
	var T int
	fmt.Fscan(reader, &T)
	for ; T > 0; T-- {
		var n, d, k int
		fmt.Fscan(reader, &n, &d, &k)
		A := make([]int, n+1)
		for i := 1; i <= n; i++ {
			fmt.Fscan(reader, &A[i])
		}

		// if A[n]-A[1] > d {
		// 	fmt.Fprintln(writer, 0)
		// 	continue
		// }

		// success := false
		// for j := n; j >= 1; j-- {
		// 	for r := 1; r <= n; r++ {

		// 	}
		// }

		// if !success {
		// 	fmt.Fprintln(writer, -1)
		// }

		success := false
		left, right := 1, 1
		for right <= n {
			if A[right]+(right-left)*k-A[left] <= d {
				// 当极差小于等于 d 时，右移 right 指针
				right++
			} else {
				// 当极差大于 d 时，左移 left 指针
				left++
				if A[right]+(right-left)*k-A[left] <= d {
					// 如果左移后极差小于等于 d 了，则返回上一个 left
					left--
					success = true
					break
				}
			}

		}

		if success {
			fmt.Fprintln(writer, right-left+1)
		} else {
			fmt.Fprintln(writer, -1)
		}
	}
}

// func operation(a, k, r, i int) int {
// 	return a + k*(r-i+1)
// }
