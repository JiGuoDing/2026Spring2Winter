package src

import "fmt"

func P1002() {
	var ax, ay, bx, by int
	// fmt.Scan() 会自动跳过空格和换行，依次填入变量，适用于数量固定的输入
	fmt.Scan(&ax, &ay, &bx, &by)

	// 表示棋盘
	board := make([][]bool, ax+1)
	for i := range board {
		board[i] = make([]bool, ay+1)
	}
	board[bx][by] = true

	// 马跳动的 8 个方向
	dx := []int{-2, -2, -1, -1, 1, 1, 2, 2}
	dy := []int{-1, 1, -2, 2, -2, 2, -1, 1}

	// 标记马的控制点
	for i := range 8 {
		cx := bx + dx[i]
		cy := by + dy[i]

		if cx >= 0 && cx <= ax && cy >= 0 && cy <= ay {
			board[cx][cy] = true
		}
	}

	// 表示每个点有多少条路径到达
	dp := make([][]int64, ax+1)
	for i := range dp {
		dp[i] = make([]int64, ay+1)
	}

	if !board[0][0] {
		dp[0][0] = 1
	}

	for i := 0; i <= ax; i++ {
		for j := 0; j <= ay; j++ {
			// 如果是马的控制点，路径数为 0
			if board[i][j] {
				dp[i][j] = 0
				continue
			}

			if i > 0 {
				if !board[i-1][j] {
					dp[i][j] += dp[i-1][j]
				}
			}
			if j > 0 {
				if !board[i][j-1] {
					dp[i][j] += dp[i][j-1]
				}
			}
		}
	}

	fmt.Println(dp[ax][ay])
}
