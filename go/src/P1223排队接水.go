package src

import "fmt"

func P1223() {
	var n int
	fmt.Scan(&n)

	waterTime := make([]int, n)
	for i := range waterTime {
		fmt.Scan(&waterTime[i])
	}
}
