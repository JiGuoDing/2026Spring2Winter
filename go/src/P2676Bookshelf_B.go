package src

import (
	"bufio"
	"fmt"
	"os"
)

func P2676() {
	var n, b int
	// os.Stdin 代表标准输入流，类型为 *os.File
	// NewScanner 用于高效地按 "分隔符" (默认是换行符 \n) 读取输入
	scanner := bufio.NewScanner(os.Stdin)
	// 阻塞读取，每次从 os.Stdin 读取下一行 (直到遇到换行符或 EOF)
	// 返回 true 表示成功读取到一行，false 表示输入结束或发生错误
	scanner.Scan()
	// scanner.Text() 返回上一次 Scan() 读取到的字符串 (不包含换行符)
	// fmt.Sscanf 从字符串中按照格式解析数据
	fmt.Sscanf(scanner.Text(), "%d %d", &n, &b)

	heights := make([]int, n)

	for i := range n {
		scanner.Scan()
		fmt.Sscanf(scanner.Text(), "%d", &heights[i])
	}

}
