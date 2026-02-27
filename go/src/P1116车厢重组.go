package src

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
)

func P1116() {
	scanner := bufio.NewScanner(os.Stdin)
	// 设置按照单词 (空哥 / 换行) 分割，而不是默认的按行分割
	scanner.Split(bufio.ScanWords)

	scanner.Scan()
	n, _ := strconv.Atoi(scanner.Text())

	seq := make([]int, n)
	for i := range n {
		scanner.Scan()
		seq[i], _ = strconv.Atoi(scanner.Text())
	}

	// 旋转次数
	cnt := 0

	// 如果一个数 ai 需要交换，说明在 a1 到 ai-1 有比 ai 大的数。于是枚举每一个 ai，再从 a1 遍历到 ai-1，计算区间内比 ai 大的数的个数，就是 ai 需要交换的次数。
	for i := range n {
		for j := range i {
			if seq[j] > seq[i] {
				cnt++
			}
		}
	}
	fmt.Println(cnt)
}
