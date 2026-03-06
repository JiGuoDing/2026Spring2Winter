package interviewIssue

import (
	"fmt"
	"sync"
)

// getWorkerID 是核心路由算法：根据当前数字，计算出应该交由哪个协程打印
func getWorkerID(num int) int {
	// 【核心规则】：只要尾数是 1，强制分配给协程 1
	if num%10 == 1 {
		return 1
	}

	// 对于其他数字，我们需要在协程 2 ~ 100（共99个）之间进行轮询分配。
	// 首先计算：在当前数字之前，共有多少个“尾数不是1的数字”？
	q := num / 10
	r := num % 10
	count := q * 9 // 每 10 个数字里有 9 个尾数不为 1
	if r > 1 {
		// 不统计那个尾数为 1 的数
		count += r - 1
	}

	// count 是当前数字在“非1尾数集合”中的排名
	// 通过取模运算，将其均匀映射到 2 ~ 100 这 99 个协程上
	workerID := (count-1)%99 + 2
	return workerID
}

// DynamicRelay (去中心化接力赛)
//  ├── 1. 资源初始化 (准备赛道)
//  │    ├── 创建 100 个 Worker 专属的无缓冲通道
//  │    ├── 创建 1 个全局 done 通道 (用于广播比赛结束)
//  │    └── 设置 WaitGroup 等待 100 个选手完赛
//  │
//  ├── 2. 启动协程 (选手就位)
//  │    └── 开启 100 个 goroutine，内部运行无限循环 + select 多路复用
//  │         ├── 分支 A: 收到属于自己的数字 (case num := <-chans[id])
//  │         │    ├── [执行] 打印数字
//  │         │    ├── [检查] 发现数字是 1000？ -> 触发全局广播 close(done)，当前退出
//  │         │    └── [接力] 数字还没到 1000：
//  │         │         ├── num + 1 算出下一个数字
//  │         │         ├── 调用 getWorkerID 算出该传给几号选手
//  │         │         └── 发送到对应选手的通道中
//  │         │
//  │         └── 分支 B: 收到比赛结束广播 (case <-done)
//  │              └── 直接 return 退出，释放资源
//  │
//  ├── 3. 启动引擎 (发令枪响)
//  │    └── 主协程向 chans[1] 塞入数字 `1`，激活整个链路
//  │
//  └── 4. 完美收官 (等待散场)
//       └── wg.Wait() 阻塞，直到 100 个协程全部安全退出

func DynamicRelay() {
	const numGoroutines = 100
	const maxPrint = 1000

	// 1. 创建 101 个无缓冲通道（索引 1~100 对应 100 个协程，忽略 0）
	chans := make([]chan int, numGoroutines+1)
	for i := 1; i <= numGoroutines; i++ {
		chans[i] = make(chan int)
	}

	// 用于通知所有协程安全退出的全局广播通道
	done := make(chan struct{})
	var wg sync.WaitGroup
	wg.Add(numGoroutines)

	// 2. 启动 100 个协程
	for i := 1; i <= numGoroutines; i++ {
		go func(id int) {
			defer wg.Done()
			for {
				select {
				case num := <-chans[id]:
					// 收到上一个协程传来的数字，执行打印
					fmt.Printf("协程 %d: %d\n", id, num)

					// 如果已经打印到 1000，触发退出机制
					if num == maxPrint {
						close(done) // 关闭 done 通道，广播通知所有协程退出
						return
					}

					// 计算下一个数字应该由哪个协程打印
					nextNum := num + 1
					nextID := getWorkerID(nextNum)

					// 将数字动态传递给对应的协程
					chans[nextID] <- nextNum

				case <-done:
					// 收到结束信号，直接退出
					return
				}
			}
		}(i)
	}

	// 3. 启动开关：主协程将数字 1 发给协程 1，启动整个动态接力链
	chans[1] <- 1

	// * 这里不需要显示 close(chans[i]) 因为 goroutine 能正确退出，退出后这些 channel 就没有引用了，GC 会自动回收

	// 等待所有协程完美退出
	wg.Wait()
	fmt.Println("打印完成！")
}

// Master-Worker 调度模式 (代码名: TokenRing)
//  ├── 1. 资源初始化 (包工头准备工具)
//  │    ├── 创建 100 个 Worker 的任务通道
//  │    ├── 创建 1 个全局 ACK 通道 (核心：保证顺序的确认机制)
//  │    └── 设置 WaitGroup 计数 100
//  │
//  ├── 2. 启动协程 (工人就位，纯干活)
//  │    └── 开启 100 个 goroutine，内部运行 for range 循环
//  │         ├── 阻塞等待老板发任务 (通道不关闭，循环不结束)
//  │         ├── [执行] 收到数字 -> 打印
//  │         └── [汇报] 向 ACK 通道发送一个空结构体，告诉老板“完事了”
//  │
//  ├── 3. 主协程分发任务 (包工头派活，1-1000循环)
//  │    └── for num = 1 到 1000:
//  │         ├── [路由计算]
//  │         │    ├── 尾数是1？ -> 分给 1 号工人
//  │         │    └── 其他尾数？ -> 按照 2~100 轮流平摊 (otherWorkId 轮转)
//  │         │
//  │         ├── [派发] 将 num 发送到选中工人的通道 (channels[targetID] <- num)
//  │         │
//  │         └── [阻塞等待] 读取 ACK 通道 (<-ack)
//  │              └── ⚠️ 绝对阻塞！必须等刚刚那个工人干完活，才进入下一次循环
//  │
//  └── 4. 完美收官 (宣布下班)
//       ├── 循环结束，任务全部分发完毕
//       ├── 遍历关闭 1-100 号工人的任务通道 (触发工人 for range 自动结束)
//       └── wg.Wait() 等待所有工人收拾工具下班

// 调度器模式，用一个中心化的“主协程”来控制所有的分发逻辑，由它来决定哪个数字发给哪个通道
// 必须加一个确认机制 (ACK)：主协程把数字发给某一个协程后，必须阻塞等待，直到那个协程说“我打印完了”，主协程才能发出下一个数字。
func TokenRing() {
	const (
		numGoroutines = 100
		maxPrint      = 1000
	)

	// 创建 100 个工作通道 (索引 1 - 100)
	channels := make([]chan int, numGoroutines+1)
	for i := 1; i <= numGoroutines; i++ {
		channels[i] = make(chan int)
	}

	// 创建一个 ACK 通道，确保输出顺序
	ack := make(chan struct{})

	var wg sync.WaitGroup

	// 启动 100 个 worker goroutine，它们只负责：接收 -> 打印 -> 回复确认
	for i := 1; i <= numGoroutines; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			// for range 会不断从通道获取数据，直到通道被 close (这是退出这个循环的唯一条件)，因此在主协程中必须显示 close(channels[i])
			for num := range channels[id] {
				// 执行打印
				fmt.Printf("协程 %d: %d\n", id, num)
				// 打印完成后，向主协程发送确认信号
				ack <- struct{}{}
			}
		}(i)
	}

	// 主协程作为 Dispatcher (调度器)
	// 负责吧 1-1000 发送到通道

	otherWorkId := 2
	for num := 1; num <= maxPrint; num++ {
		targetID := 0

		// 路由规则：尾数为 1 的数都发给协程 1
		if num%10 == 1 {
			targetID = 1
		} else {
			// 其他数字由 2-100 号协程轮询打印
			targetID = otherWorkId
			otherWorkId++
			if otherWorkId > numGoroutines {
				// 轮转回 2 号协程
				otherWorkId = 2
			}
		}

		channels[targetID] <- num
		// 等待目标协程打印完成，确认信号发送到 ACK 通道中
		<-ack
	}

	// * GO 的一条黄金法则：由发送者负责关闭 channel
	for i := 1; i <= numGoroutines; i++ {
		close(channels[i])
	}

	wg.Wait()
	fmt.Println("打印完成")
}
