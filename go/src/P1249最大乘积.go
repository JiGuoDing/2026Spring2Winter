package src

import (
	"fmt"
)

// 大整数乘法
func BigIntMultiply(factors []int) []int {
	// 边界检查：如果输入为空，返回空
	if len(factors) == 0 {
		return []int{}
	}

	// 预处理：如果输入包含 0，则乘积直接为 0
	for _, v := range factors {
		if v == 0 {
			return []int{0}
		}
	}

	// 初始化结果为 1
	result := []int{1}

	// 遍历输入切片中的每个乘数
	for _, v := range factors {
		result = multiplyBigIntByInt(result, v)
	}

	reverse(result)

	return result
}

// 将一个大整数 (倒序切片) 乘某个普通整数
func multiplyBigIntByInt(digits []int, num int) []int {
	// 进位，使用 int64 防止中间计算溢出
	var carry int64 = 0
	n := int64(num)

	// 遍历大数的每一位
	for i := 0; i < len(digits); i++ {
		// 当前位计算：原数值 * 乘数 + 进位
		// 注意：digits[i] 是 0-9，n 可能是很大的 int，所以乘积可能超过 int 范围，需用 int64
		current := int64(digits[i])*n + carry

		// 更新当前位的结果 (取个位)
		digits[i] = int(current % 10)

		// 计算新的进位
		carry = current / 10
	}

	// 处理剩余的进位
	// 如果 carry > 0，说明结果变长了，需要 append
	for carry > 0 {
		digits = append(digits, int(carry%10))
		carry /= 10
	}

	return digits
}

// 反转切片
func reverse(digits []int) {
	for i, j := 0, len(digits)-1; i < j; i, j = i+1, j-1 {
		digits[i], digits[j] = digits[j], digits[i]
	}
}

func P1249() {
	var n int
	// 推荐使用 fmt.Scan 读取简单整数
	_, err := fmt.Scan(&n)
	if err != nil {
		return
	}

	// 1. 生成贪心序列：2, 3, 4... 直到 sum >= n
	factors := make([]int, 0)
	sum := 0
	i := 2
	for ; sum < n; i++ {
		factors = append(factors, i)
		sum += i
	}

	// 2. 计算溢出值
	excess := sum - n

	// 3. 构造最终的输出序列
	finalFactors := make([]int, 0)

	if excess == 1 {
		// 特殊情况：如果溢出 1，不能删去 1 (不存在)，也不能只删去 2 (会导致和变为 n-1)。
		// 策略：删去 2，并将最后一个数 +1。
		// 原序列类似: 2, 3, ..., k
		// 修改后: 3, ..., k+1
		for j := 0; j < len(factors); j++ {
			if factors[j] == 2 {
				continue // 跳过 2
			}
			if j == len(factors)-1 {
				finalFactors = append(finalFactors, factors[j]+1) // 最后一个数加 1
			} else {
				finalFactors = append(finalFactors, factors[j])
			}
		}
	} else {
		// 一般情况：直接删去等于 excess 的那个数
		// 如果 excess 为 0，则不删去任何数
		for _, v := range factors {
			if v == excess {
				continue
			}
			finalFactors = append(finalFactors, v)
		}
	}

	// 4. 输出拆分方案
	// 大数乘法初始化为 1
	bigResult := []int{1}

	for idx, v := range finalFactors {
		fmt.Printf("%d", v)
		if idx < len(finalFactors)-1 {
			fmt.Print(" ")
		}
		// 累乘
		bigResult = multiplyBigIntByInt(bigResult, v)
	}
	fmt.Println()

	// 5. 输出乘积 (需要倒序输出)
	for i := len(bigResult) - 1; i >= 0; i-- {
		fmt.Printf("%d", bigResult[i])
	}
	fmt.Println()
}
