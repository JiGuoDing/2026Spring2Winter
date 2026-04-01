package interviewIssue

import (
	"bufio"
	"fmt"
	"os"
)

func Exchange() {
	reader, writer := bufio.NewReaderSize(os.Stdin, 1<<20), bufio.NewWriterSize(os.Stdout, 1<<20)
	defer writer.Flush()

	var T, n, k int
	fmt.Fscan(reader, &T)
	for ; T > 0; T-- {
		fmt.Fscan(reader, &n, &k)
		nums := make([]int, n)
		for i := 0; i < n; i++ {
			fmt.Fscan(reader, &nums[i])
		}

		times := n / k
		for ; times > 0; times-- {
			for i := 0; i < n-k; i++ {
				if nums[i] < nums[i+k] {
					nums[i], nums[i+k] = nums[i+k], nums[i]
				}
			}
		}
		for idx, num := range nums {
			if idx == n-1 {
				fmt.Printf("%d\n", num)
			} else {
				fmt.Printf("%d ", num)
			}
		}
	}
}
