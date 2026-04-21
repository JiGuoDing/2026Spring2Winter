package interviewIssue

/**
 * SnakeGame 贪吃蛇游戏类
 * 设计思路：
 * 1. 使用双端队列（Go 中用切片模拟）存储蛇身坐标，其中 index 0 为蛇头。
 * 2. 使用哈希表 (map) 存储蛇身占据的所有位置，以便在 O(1) 时间内判断是否撞到自己。
 * 3. 坐标转换：将二维坐标 (row, col) 转换为一维索引 row * width + col，方便存储在 map 中。
 */
type SnakeGame struct {
	width, height int          // 棋盘的宽度和高度
	food          [][]int      // 食物的位置列表，按顺序出现
	foodIndex     int          // 当前等待被吃掉的食物在 food 列表中的索引
	snake         [][]int      // 蛇身坐标列表，[0] 始终是蛇头，末尾是蛇尾
	occupied      map[int]bool // 记录蛇身当前占据的所有格子（一维化坐标），用于快速碰撞检测
	score         int          // 当前得分（吃掉的食物数量）
}

/**
 * Constructor 初始化游戏
 * @param width 棋盘宽度
 * @param height 棋盘高度
 * @param food 食物列表
 */
func Constructor(width int, height int, food [][]int) SnakeGame {
	// 初始状态下，蛇位于左上角 (0, 0)，长度为 1
	snake := [][]int{{0, 0}}
	// 记录初始蛇身位置
	occupied := map[int]bool{0: true}

	return SnakeGame{
		width:     width,
		height:    height,
		food:      food,
		foodIndex: 0,
		snake:     snake,
		occupied:  occupied,
		score:     0,
	}
}

/**
 * Move 移动蛇
 * @param direction 移动方向："U" (上), "D" (下), "L" (左), "R" (右)
 * @return 移动后的得分，如果游戏结束则返回 -1
 */
func (this *SnakeGame) Move(direction string) int {
	// 1. 获取当前蛇头的坐标
	headRow, headCol := this.snake[0][0], this.snake[0][1]

	// 2. 根据移动方向，计算新蛇头的预想坐标
	switch direction {
	case "U": // Up: 行索引减小
		headRow--
	case "D": // Down: 行索引增加
		headRow++
	case "L": // Left: 列索引减小
		headCol--
	case "R": // Right: 列索引增加
		headCol++
	}

	// 3. 边界检查：判断新蛇头是否超出了棋盘范围（撞墙）
	if headRow < 0 || headRow >= this.height || headCol < 0 || headCol >= this.width {
		return -1
	}

	// 4. 获取当前蛇尾的信息，为后续移动逻辑做准备
	tailRow, tailCol := this.snake[len(this.snake)-1][0], this.snake[len(this.snake)-1][1]
	tailKey := tailRow*this.width + tailCol

	// 5. ⭐ 核心避坑逻辑：
	// 在检查新蛇头是否撞到自己之前，先临时将“旧蛇尾”从 occupied 集合中移除。
	// 理由：如果蛇移动时没有吃到食物，蛇尾会向前移动一位，腾出当前位置。
	// 此时，如果新蛇头刚好移动到旧蛇尾的位置，是不算“撞到自己”的。
	delete(this.occupied, tailKey)

	// 6. 身体碰撞检查：判断新蛇头是否移动到了当前蛇身占据的位置
	headKey := headRow*this.width + headCol
	if this.occupied[headKey] {
		// 撞到了自己的身体，游戏结束
		// 补偿逻辑：虽然游戏结束了，但为了保持状态一致性，可以将刚才移除的蛇尾加回去
		this.occupied[tailKey] = true
		return -1
	}

	// 7. 更新蛇头位置：将新蛇头坐标插入到 snake 数组的最前面，并更新 occupied 集合
	this.snake = append([][]int{{headRow, headCol}}, this.snake...)
	this.occupied[headKey] = true

	// 8. 食物处理逻辑
	// 检查新蛇头位置是否正好有食物可以吃
	if this.foodIndex < len(this.food) &&
		this.food[this.foodIndex][0] == headRow &&
		this.food[this.foodIndex][1] == headCol {

		// 情况 A：吃到食物
		this.score++     // 得分加 1
		this.foodIndex++ // 准备下一次出现的食物
		// 蛇身变长：由于在第 7 步已经添加了新头，且此处不移除蛇尾，蛇的总长度自然增加 1
	} else {
		// 情况 B：没有吃到食物
		// 移除旧蛇尾：保持蛇的总长度不变（对应“蛇向前爬行一步”的视觉效果）
		this.snake = this.snake[:len(this.snake)-1]
		// 注意：此时不需要再次 delete(occupied, tailKey)，因为第 5 步已经删过了
	}

	return this.score
}
