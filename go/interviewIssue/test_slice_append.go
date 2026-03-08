package interviewIssue

import "fmt"

func f(s []int) []int {
	s = append(s, 100)
	return s
}

func fPtr(s *[]int) {
	*s = append(*s, 10)
}

func appendAndPrint(slice []int) {
	fmt.Printf("slice start: %p\n", slice)
	slice = append(slice, 4)
	fmt.Printf("slice end: %p\n", slice)
}

func TestSliceAppend() {
	s := make([]int, 3)
	fmt.Println("s:", s)
	appendAndPrint(s)
	fmt.Println("s:", s)
	fmt.Printf("main slice: %p\n", s) // 地址不同了
}

func TestSliceMain() {
	s := []int{0, 0}
	newS := f(s)

	fmt.Println("s:", s)       // 输出: [0 0]
	fmt.Println("newS:", newS) // 输出: [0 0 100]

	s = newS // 此时 s 变成了 [0 0 100]

	fPtr(&s)
	fmt.Println("s after fPtr:", s) // 输出: [0 0 100 10]
}
