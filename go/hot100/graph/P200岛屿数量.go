package graph

type coordinate struct {
	x int
	y int
}

func numIslands(grid [][]byte) int {
	// 处理边界情况
	if len(grid) == 0 {
		return 0
	}

	iterationCnt := 0
	rows, columns := len(grid), len(grid[0])
	auxiliaryQueue := make([]coordinate, 0)
	offsets := [][]int{{-1, 0}, {1, 0}, {0, -1}, {0, 1}}

	for rowNum, row := range grid {
		for columnNum, ele := range row {
			// 如果该坐标是 0 说明是水域或者是已经被访问过的岛屿
			if ele == '0' {
				continue
			}
			// 该坐标是 1，说明是一个新的岛屿，BFS 遍历该岛屿的坐标
			iterationCnt++
			auxiliaryQueue = append(auxiliaryQueue, coordinate{rowNum, columnNum})
			grid[rowNum][columnNum] = '0'
			for len(auxiliaryQueue) != 0 {
				// 弹出队头坐标
				currentCoordinate := auxiliaryQueue[0]
				auxiliaryQueue = auxiliaryQueue[1:]

				for _, offset := range offsets {
					nextCoordinateX, nextCoordinateY := currentCoordinate.x+offset[0], currentCoordinate.y+offset[1]
					// 判断下一坐标是否合法
					if nextCoordinateX >= 0 && nextCoordinateX < rows && nextCoordinateY >= 0 && nextCoordinateY < columns {
						// 下一个坐标是水域，跳过
						if grid[nextCoordinateX][nextCoordinateY] == '0' {
							continue
						}
						// 下一个坐标是陆地，加入辅助队列
						auxiliaryQueue = append(auxiliaryQueue, coordinate{nextCoordinateX, nextCoordinateY})
						grid[nextCoordinateX][nextCoordinateY] = '0'
					}
				}
			}
		}
	}

	return iterationCnt
}
