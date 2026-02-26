package src

import (
	"bufio"
	"fmt"
	"os"
)

func P1116() {
	scanner := bufio.NewScanner(os.Stdin)
	scanner.Scan()

	var n int
	fmt.Sscanf(scanner.Text(), "%d", &n)
	seq := make([]int, n)
	for i := range n {
		scanner.Scan()
		fmt.Sscanf(scanner.Text(), "%d", &seq[i])
	}

	// 旋转次数
	cnt := 0

}
