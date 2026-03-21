package dynamicProgramming

func generate(numRows int) [][]int {
	var triangle [][]int
	var row []int = []int{1}
	triangle = append(triangle, append([]int{}, row...))

	for i := 1; i < numRows; i++ {
		lastRow := append([]int{}, row...)
		row = make([]int, i+1)
		for idx, num := range lastRow {
			row[idx] += num
			row[idx+1] += num
		}
		triangle = append(triangle, append([]int{}, row...))
	}

	return triangle
}
