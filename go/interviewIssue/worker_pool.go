package interviewIssue

import (
	"context"
	"fmt"
	"log/slog"
	"math/rand"
	"sync"
	"sync/atomic"
	"time"
)

/*
题目：实现一个并发任务处理池 (Worker Pool)

题目背景与目的
在后端开发中，我们经常面临大量并发任务需要处理的场景，例如同时处理海量 HTTP 请求、批量数据处理等。如果为每个任务都新建一个 goroutine，会导致 goroutine 数量失控，消耗大量内存。

Worker Pool 是解决这个问题的经典模式：预先创建固定数量的 worker goroutine，任务通过 channel 分发给这些 worker 处理。

题目要求
请实现一个 并发 Worker Pool，满足以下需求：

并发处理：支持指定数量的 worker goroutine 并发处理任务
任务队列：任务通过 buffered channel 排队，队列满时提交阻塞等待
超时控制：每个任务有独立的超时时间 (2 秒)，超时自动取消
结果收集：异步收集所有任务的执行结果
优雅关闭 (Graceful Shutdown)：停止接受新任务，但等待队列中已有的任务全部执行完毕
强制关闭 (Force Shutdown)：立即取消所有任务，所有 worker 立即退出
统计信息：统计成功/失败任务数，要求线程安全
*/

// ================================================================
// * Part 1: 数据结构定义
// ================================================================

// Task 代表一个待执行的任务
// Execute 是任务的核心逻辑函数，接受 context 以支持超时和取消
type Task struct {
	ID      int
	Execute func(ctx context.Context) error
}

// Result 代表一个任务的执行结果
type Result struct {
	TaskID  int
	Error   error
	Elapsed time.Duration
}

// WorkerPool 是并发任务处理池的核心结构体
type WorkerPool struct {
	workerCount int         // worker goroutine 的数量
	taskQueue   chan Task   // 任务队列：producer 写入，worker 读取
	resultCh    chan Result // 结果队列：worker 写入，外部读取

	wg     sync.WaitGroup     // 用于等待所有 worker goroutine 退出
	ctx    context.Context    // 全局 context，用于 ForceShutdown
	cancel context.CancelFunc // 对应的取消函数

	// 使用原子操作保证并发安全，比 mutex 性能更高
	successCount int64 // 成功任务数
	failCount    int64 // 失败任务数
}

// ================================================================
// * Part 2: 构造与启动
// ================================================================

// NewWorkerPool 创建一个新的 WorkerPool 实例
// workerCount: 并发 worker goroutine 的数量
// queueSize: 任务队列的缓冲容量
func NewWorkerPool(workerCount int, queueSize int) *WorkerPool {
	// 创建一个可手动取消的根 context，用于 ForceShutdown 场景
	ctx, cancel := context.WithCancel(context.Background())

	return &WorkerPool{
		workerCount: workerCount,
		// buffered channel：允许 producer 在 worker 未就绪时先将任务入队，减少阻塞
		taskQueue: make(chan Task, queueSize),
		// 结果队列稍大一些，避免 worker 因写不进结果而阻塞过久
		resultCh: make(chan Result, queueSize),
		ctx:      ctx,
		cancel:   cancel,
	}
}

// Start 启动 WorkerPool，创建 workerCount 个 worker goroutine
func (wp *WorkerPool) Start() {
	for i := 0; i < wp.workerCount; i++ {
		// 在启动 goroutine 前调用 Add，避免竞争条件
		wp.wg.Add(1)
		// 每个 worker 都是一个独立的 goroutine
		go wp.worker(i)
	}

	// 启动一个用于收尾的 goroutine
	// 等待所有 worker 退出后，关闭 resultCh
	// 这样外部通过 `for range pool.Result()` 消费时，能感知到结束并自然退出循环
	// 关键点：这个 goroutine 不需要加入 WatiGroup，因为它本身就是在等待 WaitGroup
	go func() {
		wp.wg.Wait()       // 阻塞直到所有 worker goroutine 都调用了 wg.Done()
		close(wp.resultCh) // 关闭结果 channel，通知消费方所有结果已产出
		slog.Info("[Pool] All workers exited, result channel closed")
	}()
}

// ================================================================
// * Part 3: Worker 核心逻辑 (最关键的部分)
// ================================================================

// worker 是每个 goroutine 执行的核心函数
// 它在一个无限循环中监听两个信号：
//  1. 从 taskQueue 中取到任务 -> 执行
//  2. ctx 被取消 (ForceShutdown) -> 立即退出
func (wp *WorkerPool) worker(id int) {
	// defer 确保无论以何种方式退出，都会调用 wg.Done()
	// 这是防止 WaitGroup 死锁的关键
	defer wp.wg.Done()

	slog.Info("worker started", "id", id)

	for {
		// select 实现多路复用，同时监听多个 channel
		// 当多个 case 同时就绪时，Go 随机选择一个执行
		select {
		// Case 1: 全局 context 被取消 (ForceShutdown 调用了 cancel())
		// 立即退出，不再处理任何任务
		case <-wp.ctx.Done():
			slog.Warn("worker canceled", "id", id)
			return

		// Case 2: 从 taskQueue 中取到任务
		case task, ok := <-wp.taskQueue:
			// ok 为 false 表示 taskQueue 已关闭
			// 即 Shutdown 被调用，且队列中所有任务已全部取完
			if !ok {
				slog.Info("taskQueue closed", "id", id)
				return
			}

			// ----- 执行任务 -----
			// 为当前任务创建独立的、带超时的 context
			// 父 context 是 wp.ctx：若 ForceShutdown() 被调用，任务也会被取消
			taskCtx, taskChannel := context.WithTimeout(wp.ctx, 2*time.Second)

			start := time.Now()
			// 执行任务核心逻辑
			err := task.Execute(taskCtx)
			elapsed := time.Since(start)

			// 立即调用 taskCancel()，释放 Context 相关资源
			// 即使 WithTimeout 会自动取消，也应该显示调用，这是 Go 最佳实践
			// 否则在 timeout 到期前，context 的资源 (如 timer) 不会被释放
			taskChannel()

			// 用原子操作更新计数器，无需加锁，性能更优
			if err != nil {
				atomic.AddInt64(&wp.failCount, 1)
			} else {
				atomic.AddInt64(&wp.successCount, 1)
			}

			// 将结果写入结果 channel
			// 同样用 select 防止：当 ForceShutdown 时，resultCh 满了导致 goroutine 永久阻塞
			// 这是防止 goroutine 泄漏的关键技巧
			select {
			case wp.resultCh <- Result{TaskID: task.ID, Error: err, Elapsed: elapsed}:
			case <-wp.ctx.Done():
				slog.Warn("Worker force shutdown while writing result, exiting", "id", id)
				return
			}
		}
	}
}

// ================================================================
// * Part 4: 对外暴露的 API
// ================================================================

// Submit 向队列提交一个任务
// 若队列已满，会阻塞等待空位；若 pool 已被强制关闭，返回错误
func (wp *WorkerPool) Submit(task Task) error {
	select {
	case wp.taskQueue <- task:
		return nil
	case <-wp.ctx.Done():
		return fmt.Errorf("pool is force-shutdown, task %d rejected", task.ID)
	}
}

// Results 返回只读的结果 channel (channel 方向限定：只读 <-chan)
// 调用方法使用 for range 消费，resultCh 关闭后 range 自动退出
func (wp *WorkerPool) Results() <-chan Result {
	return wp.resultCh
}

// Shutdown 优雅关闭
// 关闭 taskQueue 通知 worker 不再有新任务
// 已在队列中的任务会被 worker 继续处理完毕
// 【注意】此函数不阻塞，通过 for range Results() 感知完成
func (wp *WorkerPool) Shutdown() {
	// close(taskQueue) 有两个效果：
	// 1. 已缓冲在 channel 中的任务仍可被读取 (worker 会继续处理)
	// 2. 队列排空后，worker 读到的 ok == false，正常退出
	close(wp.taskQueue)
}

// ForceShutdown 强制关闭
// 取消全局 context，所有 worker 和正在执行的任务都会感知到 ctx.Done()
// worker 在下一次 select 时立即退出，正在执行的任务也会收到取消信号
func (wp *WorkerPool) ForceShutdown() {
	wp.cancel()
}

// Stats 安全地读取统计数据
func (wp *WorkerPool) Stats() (success, fail int64) {
	return atomic.LoadInt64(&wp.successCount), atomic.LoadInt64(&wp.failCount)
}

// ================================================================
// * Part 5: 模拟任务 - 模拟 HTTP 请求处理
// ================================================================

// newHTTPTask 创建一个模拟 HTTP 请求处理的任务
//
// latency: 模拟的网络 I/O 耗时
// shouldFail: 是否模拟服务端 500 错误
func newHTTPTask(id int, latency time.Duration, shouldFail bool) Task {
	return Task{
		ID: id,
		Execute: func(ctx context.Context) error {
			// 用 select 模拟可取消的网络 I/O
			// - 正常路径：等待 latency 后完成
			// - 超时/取消路径：ctx.Done() 触发，提前退出 (这是 context 的核心用途)
			select {
			case <-time.After(latency):
				if shouldFail {
					return fmt.Errorf("HTTP 500: internal server error")
				}
				// 请求成功
				return nil
			case <-ctx.Done():
				// ctx.Error() 会返回 context.DeadlineExceeded 或 context.Canceled
				return fmt.Errorf("request cancelled or timed out: %v", ctx.Err())
			}
		},
	}
}

// ================================================================
// * Part 6: main 函数 - 演示完整流程
// ================================================================

func TestWorkerPool() {
	rand.Seed(time.Now().UnixNano())

	const (
		workerCount = 3  // 3 个并发 worker goroutine
		queueSize   = 5  // 任务队列最多缓存 5 个
		taskCount   = 12 // 总共提交 12 个任务
	)

	slog.Info("=== worker pool demo start ===")

	// Step 1：创建并启动 WorkerPool
	pool := NewWorkerPool(workerCount, queueSize)
	pool.Start()

	// Step 2：在独立 goroutine 中提交任务 (非阻塞地将任务塞入队列)
	go func() {
		for i := 1; i <= taskCount; i++ {
			// 模拟不同响应时间：200ms ~ 3000ms
			latency := time.Duration(rand.Intn(2800)+200) * time.Millisecond
			// 模拟 30% 的任务失败
			shouldFail := rand.Intn(10) < 3

			task := newHTTPTask(i, latency, shouldFail)

			if err := pool.Submit(task); err != nil {
				slog.Error("[Main] Task submit failed", "id", i, "err", err)
				continue
			}
			slog.Info("[Main] Task submitted", "id", i, "latency", latency, "shouldFail", shouldFail)
		}

		// Step 3：所有任务提交完毕，发起优雅关闭
		slog.Info("[Main] All tasks submitted. Initiating graceful shutdown...")
		pool.Shutdown()
	}()

	// Step 4：在主 goroutine 中消费结果
	// range 会持续读取，直到 resultCh 关闭 (即所有 worker 退出后)
	for result := range pool.Results() {
		if result.Error != nil {
			slog.Error("[Main] Task failed", "id", result.TaskID, "err", result.Error)
		} else {
			slog.Info("[Main] Task succeeded", "id", result.TaskID, "elapsed", result.Elapsed)
		}
	}

	// Step 5：所有结果消费完毕，打印最终统计信息
	success, fail := pool.Stats()
	slog.Info("[Main] WorkerPool stats:", "success", success, "fail", fail)
	slog.Info("=== worker pool demo end ===")
}
