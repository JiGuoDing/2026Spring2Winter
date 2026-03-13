package interviewIssue

import (
	"os"
	"time"
)

func WriteWithoutBuffer() {
	file, _ := os.Create("test_nobuf.txt")
	defer file.Close()

	data := []byte("a") // 每次只写 1 个字节

	start := time.Now()
	// 循环写入 10000 次，每次都触发一次系统调用！
	for i := 0; i < 10000; i++ {
		file.Write(data) // 10000 次系统调用，非常低效
	}
	// 耗时会明显高于带缓冲的写入
	println("无缓冲写入耗时:", time.Since(start).String())
}
