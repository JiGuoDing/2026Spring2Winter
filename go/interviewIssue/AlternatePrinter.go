package interviewIssue

import (
	"fmt"
	"sync"
)

// 三个 goroutine 交替打印 abc 10 次
func AlternatePrinter() {
	const (
		TARGET_STRING       = "abc"
		TARGET_REPEAT_TIMES = 10
		GOROUTINE_NUM       = 3
	)

	// 创建 3 个信号 channel
	channels := make([]chan struct{}, GOROUTINE_NUM)
	for i := range channels {
		// 如果不加一个缓冲区，那么循环到最后一轮时，由于 g0 已经退出了，而 g2 还想给 chan0 发送信号，就会导致死锁
		channels[i] = make(chan struct{}, 1)
	}

	var wg sync.WaitGroup

	for i := range GOROUTINE_NUM {
		wg.Add(1)

		go func(id int) {
			defer wg.Done()
			for order := range TARGET_REPEAT_TIMES {
				<-channels[id]
				// fmt.Printf("%c", TARGET_STRING[id])
				fmt.Printf("goroutine %d: %s for %d times\n", id, TARGET_STRING, order+1)
				// 如果不想使用带缓冲区的 chan，就在这里判断是否是最后一轮的最后一个 goroutine，如果是就不发送信号了
				// if !(order == TARGET_REPEAT_TIMES-1 && id == GOROUTINE_NUM-1) {
				// 	channels[(id+1)%GOROUTINE_NUM] <- struct{}{}
				// }
				channels[(id+1)%GOROUTINE_NUM] <- struct{}{}
			}
		}(i)
	}

	channels[0] <- struct{}{}

	wg.Wait()
	fmt.Println("三个 goroutine 交替打印 abc 10 次完成")
}
