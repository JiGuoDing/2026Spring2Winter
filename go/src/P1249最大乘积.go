package src

import (
	"bufio"
	"fmt"
	"os"
)

func P1249() {
	scanner := bufio.NewScanner(os.Stdin)

	scanner.Scan()
	line := scanner.Text()
	var n int
	fmt.Sscanf(line, "%d", &n)

	// ? 思路：进行递归拆解，每次将当前数拆为两个数，乘积最大的情况为拆为两个相等或相邻的数，如果相等则只拆一个
	// ? 用 map[int]struct{} 模拟集合，存储已出现的数字
	seen := make(map[int]struct{})

}
