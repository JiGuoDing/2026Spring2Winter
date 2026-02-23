package src

import (
	"fmt"
	"sort"
)

// 定义一个结构体，表示每一个帮派成员
type Person struct {
	name     string // 名字
	position string // 职位
	banggong int    // 帮贡
	level    int    // 等级
	index    int    // 输入时的顺序（用于稳定排序）
}

func P1786() {
	var n int
	fmt.Scan(&n)

	// 存储所有人
	all := make([]Person, n)

	// 存储可以调整职位的人（排除帮主和副帮主）
	var adjustable []Person

	for i := 0; i < n; i++ {
		fmt.Scan(&all[i].name, &all[i].position, &all[i].banggong, &all[i].level)
		all[i].index = i // 记录输入顺序

		// 如果不是帮主和副帮主，就加入可调整数组
		if all[i].position != "BangZhu" && all[i].position != "FuBangZhu" {
			adjustable = append(adjustable, all[i])
		}
	}

	// ==========================
	// 第一轮排序：按帮贡排序
	// ==========================

	sort.Slice(adjustable, func(i, j int) bool {
		// 帮贡高的排前面
		if adjustable[i].banggong != adjustable[j].banggong {
			return adjustable[i].banggong > adjustable[j].banggong
		}
		// 帮贡相同，按输入顺序排
		return adjustable[i].index < adjustable[j].index
	})

	// ==========================
	// 重新分配职位
	// ==========================

	for i := 0; i < len(adjustable); i++ {
		rank := i + 1 // 排名从1开始

		switch {
		case rank >= 1 && rank <= 2:
			adjustable[i].position = "HuFa"
		case rank >= 3 && rank <= 6:
			adjustable[i].position = "ZhangLao"
		case rank >= 7 && rank <= 13:
			adjustable[i].position = "TangZhu"
		case rank >= 14 && rank <= 38:
			adjustable[i].position = "JingYing"
		default:
			adjustable[i].position = "BangZhong"
		}
	}

	// ==========================
	// 把更新后的职位同步回 all 数组
	// ==========================

	for i := 0; i < len(adjustable); i++ {
		for j := 0; j < n; j++ {
			if adjustable[i].name == all[j].name {
				all[j].position = adjustable[i].position
				break
			}
		}
	}

	// ==========================
	// 第二轮排序：乐斗显示排序
	// ==========================

	// 定义职位优先级（数字越小级别越高）
	positionRank := map[string]int{
		"BangZhu":   1,
		"FuBangZhu": 2,
		"HuFa":      3,
		"ZhangLao":  4,
		"TangZhu":   5,
		"JingYing":  6,
		"BangZhong": 7,
	}

	sort.Slice(all, func(i, j int) bool {
		// 1️⃣ 职位高的在前
		if positionRank[all[i].position] != positionRank[all[j].position] {
			return positionRank[all[i].position] < positionRank[all[j].position]
		}
		// 2️⃣ 等级高的在前
		if all[i].level != all[j].level {
			return all[i].level > all[j].level
		}
		// 3️⃣ 输入顺序靠前的在前
		return all[i].index < all[j].index
	})

	// ==========================
	// 输出结果
	// ==========================

	for i := 0; i < n; i++ {
		fmt.Println(all[i].name, all[i].position, all[i].level)
	}
}
