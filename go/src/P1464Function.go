package src

import (
	"bufio"
	"fmt"
	"os"
)

func w(a, b, c int64, dp *[21][21][21]int64) int64 {
	if a <= 0 || b <= 0 || c <= 0 {
		return 1
	}

	if a > 20 || b > 20 || c > 20 {
		return w(20, 20, 20, dp)
	}

	if dp[a][b][c] != 0 {
		return dp[a][b][c]
	}
	if a < b && b < c {
		dp[a][b][c] = w(a, b, c-1, dp) + w(a, b-1, c-1, dp) - w(a, b-1, c, dp)
	} else {
		dp[a][b][c] = w(a-1, b, c, dp) + w(a-1, b-1, c, dp) + w(a-1, b, c-1, dp) - w(a-1, b-1, c-1, dp)
	}
	return dp[a][b][c]
}

func P1464() {

	var a, b, c int64
	reader := bufio.NewReaderSize(os.Stdin, 1<<20)
	write := bufio.NewWriterSize(os.Stdout, 1<<20)
	defer write.Flush()

	// 切片的切片的切片 (动态)
	// 内存不连续、指针开销极大、创建成本高；访问 dp[i][j][k] 时 CPU 需要进行三次指针寻址，因为内存不连续，极易导致 CPU 缓存未命中
	// 每次调用 make 都会在堆上分配一块新的内存，这会导致内存碎片化，需要执行 1 + 21 + 21 * 21 = 463 次 make 内存分配
	// dp := make([][][]int64, 21)
	// for i := range dp {
	// 	dp[i] = make([][]int64, 21)
	// 	for j := range dp[i] {
	// 		dp[i][j] = make([]int64, 21)
	// 	}
	// }

	// 三维数组 (静态)
	// 内存绝对连续，它在内存中是一块连续的空间，大小是 21 * 21 * 21 * 8 = 74,088 字节
	// 零开销：没有切片头，没有指针，只是纯粹的数据挨个排列
	// 创建成本极低，如果分配在栈上，只是一条修改栈指针的指令；即使逃逸到堆上，也只是一次内存分配
	dp := [21][21][21]int64{}

	for {
		fmt.Fscan(reader, &a, &b, &c)
		if a == -1 && b == -1 && c == -1 {
			break
		}
		fmt.Fprintf(write, "w(%d, %d, %d) = %d\n", a, b, c, w(a, b, c, &dp))
	}
}
