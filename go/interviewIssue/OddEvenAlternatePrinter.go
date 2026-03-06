package interviewIssue

import (
	"fmt"
	"sync"
)

func print(id int, chIn, chOut chan int, wg *sync.WaitGroup) {
	const MAX_NUM = 1000
	defer wg.Done()

	for num := range chIn {
		fmt.Printf("goroutine %d: %d\n", id, num)
		// 及时退出，避免无限循环，避免死锁
		if num == MAX_NUM {
			break
		}
		chOut <- num + 1
		// 及时退出，避免无限循环，避免死锁
		if num+1 == MAX_NUM {
			break
		}
	}
}

// 用两个协程交替打印奇偶数
func OddEvenAlternatePrinter() {
	var wg sync.WaitGroup
	channels := make([]chan int, 2)
	for i := range channels {
		channels[i] = make(chan int)
	}
	for i := range 2 {
		wg.Add(1)
		go print(i, channels[i], channels[(i+1)%2], &wg)
	}

	channels[0] <- 0

	wg.Wait()
	fmt.Println("交替打印奇偶数完成")
}
