package matrix

type coordinate struct {
	x int
	y int
}

func spiralOrder(matrix [][]int) []int {
	if len(matrix) == 0 {
		return []int{}
	}
	rows, columns := len(matrix), len(matrix[0])
	res := make([]int, 0, rows*columns)

	// 一个 set 用于标记哪些位置已经走过
	traveled := make(map[coordinate]struct{})
	directions := []coordinate{
		{0, 1},
		{1, 0},
		{0, -1},
		{-1, 0},
	}

	currentCoordinate, currentDirection := coordinate{0, 0}, 0
	for len(res) < rows*columns {
		res = append(res, matrix[currentCoordinate.x][currentCoordinate.y])
		traveled[currentCoordinate] = struct{}{}
		// 更新当前坐标，判断合法条件
		nextcoordinate := coordinate{
			currentCoordinate.x + directions[currentDirection%4].x,
			currentCoordinate.y + directions[currentDirection%4].y,
		}
		// 如果越界
		if nextcoordinate.x < 0 || nextcoordinate.x >= rows || nextcoordinate.y < 0 || nextcoordinate.y >= columns {
			// 需要更换方向
			currentDirection++
			// 重新更新当前坐标
			nextcoordinate = coordinate{
				currentCoordinate.x + directions[currentDirection%4].x,
				currentCoordinate.y + directions[currentDirection%4].y,
			}
		}
		// 如果已经走过
		if _, ok := traveled[nextcoordinate]; ok {
			// 需要更换方向
			currentDirection++
			// 重新更新当前坐标
			nextcoordinate = coordinate{
				currentCoordinate.x + directions[currentDirection%4].x,
				currentCoordinate.y + directions[currentDirection%4].y,
			}
		}
		currentCoordinate = nextcoordinate
		// 不需要更新方向时无需其他操作
	}

	return res
}
