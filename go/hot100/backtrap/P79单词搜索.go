package backTrap

type Point struct {
	X int
	Y int
}

// 在 board 中查找 word 的第一个字符的所有可能坐标
func findByte(board [][]byte, word string) []Point {
	var points []Point
	for i := range board {
		for j := range board[i] {
			if board[i][j] == word[0] {
				points = append(points, Point{X: i, Y: j})
			}
		}
	}
	return points
}

func exist(board [][]byte, word string) bool {
	if word == "" {
		return true
	}
	if len(board) == 0 || len(board[0]) == 0 {
		return false
	}
	startPoints := findByte(board, word)
	if len(startPoints) == 0 {
		return false
	}
	rows, columns := len(board), len(board[0])
	used := make([][]bool, rows)
	for i := range rows {
		used[i] = make([]bool, columns)
	}
	// 偏移数组
	offsets := []Point{
		{X: -1, Y: 0},
		{X: 0, Y: -1},
		{X: 1, Y: 0},
		{X: 0, Y: 1},
	}

	// 记录当前字符串
	var currentStr string

	var backtrap func(point Point) bool
	backtrap = func(point Point) bool {
		// * 可修改为一个字节一个字节比较，即改为 backtrap = func(point Point, idx int)
		// if board[point.X][point.Y] != word[idx] {
		//     return false
		// }
		// if idx == len(word)-1 {  // O(1) 整数比较
		//     return true
		// }

		// 判断是否满足条件
		if currentStr == word {
			return true
		}
		if len(currentStr) >= len(word) {
			return false
		}
		// 选择：从上下左右选择，注意是否已经使用或达到边界
		for _, offset := range offsets {
			nextPoint := Point{
				X: point.X + offset.X,
				Y: point.Y + offset.Y,
			}
			// 判断是否越界
			if nextPoint.X < 0 || nextPoint.X >= rows || nextPoint.Y < 0 || nextPoint.Y >= columns {
				continue
			}
			// 判断该位置是否用过
			if used[nextPoint.X][nextPoint.Y] {
				continue
			}
			// 做选择
			currentStr += string(board[nextPoint.X][nextPoint.Y])
			used[nextPoint.X][nextPoint.Y] = true
			if backtrap(nextPoint) {
				return true
			}
			// 撤销选择
			currentStr = currentStr[:len(currentStr)-1]
			used[nextPoint.X][nextPoint.Y] = false
		}

		return false
	}

	// 找到目标字符串其实字母在网格中的位置，只要有一个起始点能完成，就说明可以
	for _, startPoint := range startPoints {
		currentStr = string(board[startPoint.X][startPoint.Y])
		used[startPoint.X][startPoint.Y] = true
		if backtrap(startPoint) {
			return true
		}
		used[startPoint.X][startPoint.Y] = false
	}
	return false
}

func existImproved(board [][]byte, word string) bool {
	if word == "" {
		return true
	}
	rows, cols := len(board), len(board[0])

	// ✅ 用二维 bool 数组替代 map，O(1) 访问无哈希开销
	used := make([][]bool, rows)
	for i := range used {
		used[i] = make([]bool, cols)
	}

	offsets := [4][2]int{{-1, 0}, {0, -1}, {1, 0}, {0, 1}}

	// ✅ 用下标 idx 替代字符串拼接，避免 O(n) 字符串操作
	var backtrack func(x, y, idx int) bool
	backtrack = func(x, y, idx int) bool {
		// ✅ 提前剪枝：字符不匹配直接返回
		if board[x][y] != word[idx] {
			return false
		}
		// 已匹配到最后一个字符
		if idx == len(word)-1 {
			return true
		}

		used[x][y] = true
		for _, off := range offsets {
			nx, ny := x+off[0], y+off[1]
			// ✅ 越界检查、访问检查、字符预检查合并，减少无效递归
			if nx >= 0 && nx < rows && ny >= 0 && ny < cols && !used[nx][ny] {
				if backtrack(nx, ny, idx+1) {
					used[x][y] = false
					return true
				}
			}
		}
		used[x][y] = false
		return false
	}

	for i := 0; i < rows; i++ {
		for j := 0; j < cols; j++ {
			if backtrack(i, j, 0) {
				return true
			}
		}
	}
	return false
}
