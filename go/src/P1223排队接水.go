package src

import (
	"fmt"
	"slices"
)

type WaterMan struct {
	cacheTime int
	index     int
}

func P1223() {
	var n int
	fmt.Scan(&n)

	waterMen := make([]WaterMan, n)
	for i := range waterMen {
		fmt.Scan(&waterMen[i].cacheTime)
		waterMen[i].index = i
	}

	slices.SortFunc(waterMen, func(a, b WaterMan) int {
		return a.cacheTime - b.cacheTime
	})

	totalWaitTime := 0.0

	for i, waterMan := range waterMen {
		totalWaitTime += float64(n-1-i) * float64(waterMan.cacheTime)
		fmt.Printf("%d ", waterMan.index+1)
	}

	fmt.Printf("\n%.2f", totalWaitTime/float64(n))
}
