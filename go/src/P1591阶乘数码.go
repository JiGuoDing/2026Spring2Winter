package src

import "fmt"

func P1591() {
	var t int
	// 读取数据组数
	if _, err := fmt.Scan(&t); err != nil {
		return
	}
	res := make([]int, t)

	for i := 0; i < t; i++ {
		var n, a int
		if _, err := fmt.Scan(&n, &a); err != nil {
			res[i] = 0
			continue
		}
		// 校验数码a的范围（0-9）
		if a < 0 || a > 9 {
			res[i] = 0
			continue
		}

		// 用切片模拟大整数，初始为1（0!和1!都是1），切片低位存数字低位
		fact := []int{1}
		// 计算n!：从2乘到n
		for j := 2; j <= n; j++ {
			carry := 0 // 进位
			// 遍历当前大整数的每一位，与j相乘
			for k := 0; k < len(fact); k++ {
				product := fact[k]*j + carry
				fact[k] = product % 10 // 当前位的结果
				carry = product / 10   // 更新进位
			}
			// 处理剩余的进位（可能有多位）
			for carry > 0 {
				fact = append(fact, carry%10)
				carry /= 10
			}
		}

		// 统计数码a出现的次数
		cnt := 0
		for _, digit := range fact {
			if digit == a {
				cnt++
			}
		}
		res[i] = cnt
	}

	// 输出结果
	for _, v := range res {
		fmt.Println(v)
	}
}
