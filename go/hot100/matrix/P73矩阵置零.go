package matrix

func setZeroes(matrix [][]int) {
	if len(matrix) == 0 {
		return
	}

	targetRows, targetColumns := make(map[int]struct{}), make(map[int]struct{})

	for rowNum, row := range matrix {
		for columnNum, ele := range row {
			if ele == 0 {
				targetRows[rowNum] = struct{}{}
				targetColumns[columnNum] = struct{}{}
			}
		}
	}

	for rowNum, _ := range targetRows {
		for col := 0; col < len(matrix[0]); col++ {
			matrix[rowNum][col] = 0
		}
	}
	for columnNum, _ := range targetColumns {
		for row := 0; row < len(matrix); row++ {
			matrix[row][columnNum] = 0
		}
	}
}

// ============================================================================
// 【优化版本 1】使用切片代替 map（减少哈希开销）
// ============================================================================

// setZeroesOptimizedV1 优化版本 1：使用布尔切片代替 map
// 优化点：
// 1. 空间复杂度：map -> 布尔切片，减少哈希表的内存开销
// 2. 时间复杂度：O(m*n) -> O(m*n)，但避免了 map 的哈希计算和冲突处理
// 3. 访问效率：数组随机访问 O(1) vs map 查找 O(1)~O(n)
func setZeroesOptimizedV1(matrix [][]int) {
	if len(matrix) == 0 || len(matrix[0]) == 0 {
		return
	}

	rows, cols := len(matrix), len(matrix[0])
	// 使用布尔切片标记需要置零的行和列
	rowHasZero := make([]bool, rows)
	colHasZero := make([]bool, cols)

	// 第一遍遍历：记录哪些行和列包含 0
	for i := 0; i < rows; i++ {
		for j := 0; j < cols; j++ {
			if matrix[i][j] == 0 {
				rowHasZero[i] = true
				colHasZero[j] = true
			}
		}
	}

	// 第二遍遍历：根据标记将对应的行列置零
	for i := 0; i < rows; i++ {
		for j := 0; j < cols; j++ {
			if rowHasZero[i] || colHasZero[j] {
				matrix[i][j] = 0
			}
		}
	}
}

// ============================================================================
// 【优化版本 2】原地算法（空间复杂度 O(1)）
// ============================================================================

// setZeroesOptimizedV2 优化版本 2：使用矩阵首行首列作为标记位
// 这是最优解！空间复杂度从 O(m+n) 降低到 O(1)
//
// 核心思想：
// 1. 用 matrix[i][0] 标记第 i 行是否需要置零
// 2. 用 matrix[0][j] 标记第 j 列是否需要置零
// 3. 特殊处理：第一行和第一列本身需要用额外变量标记
//
// 算法步骤：
// Step 1: 检查第一行和第一列是否有 0（用两个布尔变量记录）
// Step 2: 遍历除第一行第一列外的矩阵，用首行首列记录 0 的位置
// Step 3: 根据首行首列的标记，将对应位置置零
// Step 4: 根据 Step 1 的记录，处理第一行和第一列
func setZeroesOptimizedV2(matrix [][]int) {
	if len(matrix) == 0 || len(matrix[0]) == 0 {
		return
	}

	rows, cols := len(matrix), len(matrix[0])

	// Step 1: 检查第一行是否有 0
	firstRowHasZero := false
	for j := 0; j < cols; j++ {
		if matrix[0][j] == 0 {
			firstRowHasZero = true
			break
		}
	}

	// Step 2: 检查第一列是否有 0
	firstColHasZero := false
	for i := 0; i < rows; i++ {
		if matrix[i][0] == 0 {
			firstColHasZero = true
			break
		}
	}

	// Step 3: 遍历除第一行第一列外的矩阵
	// 用 matrix[i][0] 标记第 i 行，用 matrix[0][j] 标记第 j 列
	for i := 1; i < rows; i++ {
		for j := 1; j < cols; j++ {
			if matrix[i][j] == 0 {
				matrix[i][0] = 0 // 标记该行
				matrix[0][j] = 0 // 标记该列
			}
		}
	}

	// Step 4: 根据标记将对应位置置零
	// 如果 matrix[i][0] 为 0，说明第 i 行需要全部置零
	for i := 1; i < rows; i++ {
		if matrix[i][0] == 0 {
			for j := 1; j < cols; j++ {
				matrix[i][j] = 0
			}
		}
	}

	// Step 5: 根据标记将对应列置零
	// 如果 matrix[0][j] 为 0，说明第 j 列需要全部置零
	for j := 1; j < cols; j++ {
		if matrix[0][j] == 0 {
			for i := 1; i < rows; i++ {
				matrix[i][j] = 0
			}
		}
	}

	// Step 6: 处理第一行
	if firstRowHasZero {
		for j := 0; j < cols; j++ {
			matrix[0][j] = 0
		}
	}

	// Step 7: 处理第一列
	if firstColHasZero {
		for i := 0; i < rows; i++ {
			matrix[i][0] = 0
		}
	}
}

// ============================================================================
// 【三种解法对比】
// ============================================================================
//
// 原始版本 (使用 map):
//   时间复杂度：O(m*n)
//   空间复杂度：O(m+n) - map 在最坏情况下需要存储 m 行 + n 列
//   优点：代码简洁，容易理解
//   缺点：map 有哈希开销，内存占用较大
//
// 优化版本 1 (使用布尔切片):
//   时间复杂度：O(m*n)
//   空间复杂度：O(m+n) - 两个布尔切片
//   优点：避免了哈希开销，访问更快
//   缺点：空间复杂度未优化
//
// 优化版本 2 (原地算法):
//   时间复杂度：O(m*n)
//   空间复杂度：O(1) - 只用了两个布尔变量
//   优点：空间最优，面试标准答案
//   缺点：逻辑稍复杂，需要特殊处理第一行第一列
//
// 【示例演示】
// 输入:
// [
//   [1, 0, 3],
//   [4, 5, 6],
//   [7, 8, 9]
// ]
//
// 优化版本 2 执行过程:
// 1. firstRowHasZero = true (因为 matrix[0][1] = 0)
// 2. firstColHasZero = false
// 3. 遍历发现 matrix[0][1]=0，设置 matrix[0][0]=0, matrix[0][1]=0
// 4. 根据 matrix[0][1]=0，将第 2 列置零
// 5. 根据 firstRowHasZero=true，将第一行置零
//
// 输出:
// [
//   [0, 0, 0],
//   [0, 0, 0],
//   [7, 0, 9]
// ]
