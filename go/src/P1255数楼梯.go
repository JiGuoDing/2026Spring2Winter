package src

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
)

// 高精度加法
func bigAdd(bigIntA, bigIntB []int) []int {
	// 预分配结果切片，长度取参数切片长度大者
	maxLen := max(len(bigIntA), len(bigIntB))
	// 预留进位空间
	res := make([]int, 0, maxLen+1)
	carry := 0

	for i := range maxLen {
		// 防止某个切片较短，导致索引越界
		var a, b int
		if i < len(bigIntA) {
			a = bigIntA[i]
		}
		if i < len(bigIntB) {
			b = bigIntB[i]
		}

		temp := a + b + carry
		res = append(res, temp%10)
		carry = temp / 10
	}

	if carry > 0 {
		res = append(res, carry)
	}

	return res
}

func P1255() {
	scanner := bufio.NewScanner(os.Stdin)
	scanner.Split(bufio.ScanWords)

	scanner.Scan()
	n, _ := strconv.Atoi(scanner.Text())

	// 处理边界情况
	if n <= 2 {
		fmt.Println(n)
		return
	}
	// 不使用递归，因为复杂度太高 2^n
	// 使用递推
	dp := make([][]int, n+1)
	// 存储为低位在前，方便加法
	dp[1] = []int{1}
	dp[2] = []int{2}

	for i := 3; i <= n; i++ {
		dp[i] = bigAdd(dp[i-1], dp[i-2])
	}

	// 输出结果，高位在前，需要逆序打印
	res := dp[n]
	for i := range len(res) {
		fmt.Printf("%d", res[len(res)-1-i])
	}
}
