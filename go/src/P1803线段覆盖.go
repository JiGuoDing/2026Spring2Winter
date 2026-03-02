package src

import (
	"bufio"
	"fmt"
	"os"
	"slices"
)

type Game struct {
	start int
	end   int
}

func P1803() {
	var n int
	fmt.Scan(&n)

	games := make([]Game, n)
	reader := bufio.NewReaderSize(os.Stdin, 1<<20)
	for i := range games {
		fmt.Fscan(reader, &games[i].start, &games[i].end)
	}

	// 按结束时间从先到后排序
	slices.SortFunc(games, func(a, b Game) int {
		return a.end - b.end
	})

	cnt := 0
	lastEnd := 0
	for i := range n {
		if games[i].start >= lastEnd {
			cnt++
			lastEnd = games[i].end
		}
	}

	fmt.Println(cnt)
}
