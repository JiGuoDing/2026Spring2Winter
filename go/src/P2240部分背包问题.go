package src

import (
	"fmt"
	"sort"
)

type Item struct {
	// 重量
	m float64
	// 价值
	v float64
	// 单位价值
	ratio float64
}

func P2240() {

	var N int
	var T float64
	fmt.Scan(&N, &T)

	items := make([]Item, N)

	for i := range N {
		fmt.Scan(&items[i].m, &items[i].v)
		items[i].ratio = items[i].v / items[i].m
	}

	sort.Slice(items, func(i, j int) bool {
		return items[i].ratio > items[j].ratio
	})

	remain := T
	ans := 0.0

	// 依次装入：能全部装下就装全部，否则转部分并结束
	for _, item := range items {
		if remain <= 0 {
			break
		}

		if remain >= item.m {
			ans += item.v
			remain -= item.m
		} else {
			// 装入 remain 重量，对应价值 = remain * item.ratio
			ans += remain * item.ratio
			remain = 0
		}
	}

	fmt.Printf("%.2f", ans)
}
