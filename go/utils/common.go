// package声明为utils，属于库包（可被其他文件导入）
package utils

import "fmt"

// PrintSlice 打印切片（算法训练常用）
func PrintSlice(s []int) {
	fmt.Printf("切片内容: %v\n", s)
}

// ListNode 定义链表节点（链表类题目复用）
type ListNode struct {
	Val  int
	Next *ListNode
}
