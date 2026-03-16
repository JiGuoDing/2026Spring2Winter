package interviewIssue

import (
	"fmt"
	"log/slog"
	"sync"
	"sync/atomic"
	"time"
)

// 实现一个支持 TTL 和并发安全的内存缓存系统
// 核心考察：map 的并发安全、引用类型特性、遍历特性、惰性删除等
// 要求必须是并发安全的，支持多个 goroutine 同时读写
// 适用场景：可用作 HTTP 服务的接口限流计数器、会话存储 (Session Store)、热点数据缓存等

/*
NewMemCache(cleanupInterval) - 创建缓存，并启动后台定期清理
Set(key, value, ttl) - 写入缓存，ttl <= 0 表示永不过期
Get(key) - 读取缓存，过期或不存在返回 (nil, false)
Delete(key) - 删除指定 key
Keys() - 返回所有未过期的 key
Flush() - 清空所有缓存
Stats() - 返回统计信息 (有效 key 数、命中数、未命中数)
Close() - 优雅关闭，等待后台 goroutine 退出
*/

// cacheEntry 是缓存中每个条目的内部结构
type cacheEntry struct {
	value     interface{} // 存储任意类型的值
	expiresAt time.Time   // 过期时间：零值 (time.Time()) 表示永不过期
}

// isExpired 检查缓存条目是否已过期
// time.Time 的零值 IsZero() == true，永不过期的条目直接返回 false
func (ce *cacheEntry) isExpired() bool {
	if ce.expiresAt.IsZero() {
		return false
	}
	return time.Now().After(ce.expiresAt)
}

// CacheStats 对外暴露缓存统计信息
type CacheStats struct {
	ValidKeys int64 // 当前未过期的 key 数量
	Hits      int64 // 命中次数
	Misses    int64 // 未命中次数
}

// MemCache 是并发安全、支持 TTL 的内存缓存
//
// ⚠️  Go 内置的 map 不是并发安全的！
// 多个 goroutine 同时读写同一个 map，运行时会直接 panic：
//
//	"concurrent map read and map write"
//
// 必须用锁来保护所有对 map 的操作。
//
// 字段布局说明：
// hits/misses 用 int64 并配合 sync/atomic 做无锁计数；
// 在 32 位平台上，atomic 操作的 int64 需要 8 字节对齐，
// 所以原子字段放在结构体最前面是最安全的做法。
type MemCache struct {
	hits   int64 // 使用 atomic 操作，必须 64 位原子操作对齐
	misses int64 // 未命中次数，必须 64 位原子操作对齐

	mu   sync.RWMutex           // 读写锁：多读单写，保护 data map
	data map[string]*cacheEntry // 核心存储

	// 生命周期控制
	stopCh chan struct{}  // 关闭信号 channel，close() 即广播停止
	wg     sync.WaitGroup // 等待后台 goroutine 完全退出
}

// ============================================================
//  构造函数
// ============================================================

// NewMemCache 创建并启动一个 MemCache
// cleanupInterval：后台自动清理过期 key 的时间间隔
func NewMemCache(cleanupInterval time.Duration) *MemCache {
	mc := &MemCache{
		// 知识点 1：map 是引用类型，声明后必须 make 初始化才能写入！
		// 错误示例：var m map[string]*cacheEntry  → 写入会 panic
		// 正确示例：m := make(map[string]*cacheEntry)
		data: make(map[string]*cacheEntry),

		// make(chan struct{}) 创建无缓冲 channel
		// struct{} 是空结构体，大小为 0，常用作纯信号类型
		stopCh: make(chan struct{}),
	}

	mc.wg.Add(1)
	go mc.cleanupLoop(cleanupInterval)

	return mc
}

// ============================================================
//  核心 CRUD 方法
// ============================================================

// Set 写入一条缓存记录
// key:   缓存键
// value: 任意类型的值
// ttl:   存活时间；ttl <= 0 表示永不过期
func (mc *MemCache) Set(key string, value interface{}, ttl time.Duration) {
	// 写操作必须使用独占写锁 Lock()
	// 写锁会阻塞所有其他读操作和写操作，确保独占访问
	mc.mu.Lock()
	defer mc.mu.Unlock()

	ce := &cacheEntry{
		value: value,
	}
	if ttl > 0 {
		ce.expiresAt = time.Now().Add(ttl)
	}

	// 知识点 2：map 赋值语法：m[key] = value
	// 若 key 已存在则直接覆盖，Go 的 map 不区分 insert 和 update
	mc.data[key] = ce
}

// Get 读取一条缓存记录
// 返回 (value, true)  → 命中且未过期
// 返回 (nil,  false)  → 不存在或已过期
func (mc *MemCache) Get(key string) (interface{}, bool) {
	// 第一步：用读锁（RLock）检查 key 是否存在
	// RLock 允许多个 goroutine 同时持有，不互斥，适合读多写少的场景
	mc.mu.RLock()
	ce, ok := mc.data[key]
	mc.mu.RUnlock()

	// 知识点 3：map 的 comma-ok 惯用法
	// v := m[key]       → key 不存在时返回零值，无法区分"不存在"和"值为零值"
	// v, ok := m[key]   → ok=false 明确表示 key 不存在，这是判断存在性的标准写法
	if !ok {
		// key 不存在
		slog.Warn("key 不存在", "key", key)
		atomic.AddInt64(&mc.misses, 1)
		return nil, false
	}

	if ce.isExpired() {
		// key 存在但已过期 → 惰性删除 (Lazy Deletion)
		// 惰性删除：不在写入时检查，而是在读取时发现过期再删除
		// 优点：避免后台扫描的开销；缺点：过期 key 会占用内存直到被访问
		atomic.AddInt64(&mc.misses, 1)

		// 升级为写锁进行删除操作
		mc.mu.Lock()
		// ⚠️  关键：必须做 double-check (二次检查)！
		// 在 RUnlock → Lock 的间隙，其他 goroutine 可能已经：
		//   1. 将该 key 删除了
		//   2. 用 Set 刷新了该 key 的过期时间
		// 如果不做二次检查就盲目 delete，会造成逻辑错误
		if ce, ok := mc.data[key]; ok && ce.isExpired() {
			slog.Warn("key 已过期", "key", key)
			delete(mc.data, key)
		}
		mc.mu.Unlock()

		return nil, false
	}

	// 命中，记录命中次数
	slog.Info("key 命中", "key", key)
	// 命中次数加 1
	atomic.AddInt64(&mc.hits, 1)
	return ce.value, true
}

// Delete 删除指定的 key
func (mc *MemCache) Delete(key string) {
	mc.mu.Lock()
	defer mc.mu.Unlock()

	// 知识点 4：delete(map, key) 是内置函数
	// 特性：
	//   - 如果 key 不存在，是 no-op（不会 panic，直接忽略）
	//   - 如果 map 是 nil，则会 panic
	delete(mc.data, key)
}

// Keys 返回所有当前未过期的 key，顺序不稳定
func (mc *MemCache) Keys() []string {
	mc.mu.RLock()
	defer mc.mu.RUnlock()

	// 预分配 slice，避免多次扩容；容量取 map 长度（实际有效数可能更少）
	keys := make([]string, 0, len(mc.data))

	// 知识点 5：map 的遍历顺序是随机的！
	// Go 在运行时故意将 map 遍历顺序随机化，
	// 目的是防止开发者依赖某个特定的遍历顺序（那是未定义行为）。
	// 每次 for range 一个 map，得到的 key 顺序都可能不同。
	for k, ce := range mc.data {
		if !ce.isExpired() {
			keys = append(keys, k)
		}
	}

	return keys
}

// Flush 清空所有缓存条目
func (mc *MemCache) Flush() {
	mc.mu.Lock()
	defer mc.mu.Unlock()

	// 知识点 6：map 是引用类型，直接重新赋值新 map 是最高效的清空方式
	// 原来的 map 没有任何引用后，会被 GC 自动回收
	mc.data = make(map[string]*cacheEntry)

	// 补充知识：另一种清空方式——遍历时 delete
	// Go 规范明确允许在 for range 遍历 map 时 delete 任意 key（包括当前 key）
	// 这点与某些语言不同（如 Java 的 ConcurrentModificationException）
	//
	// for k := range c.data {
	//     delete(c.data, k)
	// }
}

// Stats 返回缓存统计信息
func (mc *MemCache) Stats() CacheStats {
	// atomic.LoadInt64 无锁读取原子变量，线程安全
	hits := atomic.LoadInt64(&mc.hits)
	misses := atomic.LoadInt64(&mc.misses)

	// 统计有效 key 需要遍历 map，必须加读锁
	mc.mu.RLock()
	var validKeys int64
	for _, e := range mc.data {
		if !e.isExpired() {
			validKeys++
		}
	}
	mc.mu.RUnlock()

	return CacheStats{
		ValidKeys: validKeys,
		Hits:      hits,
		Misses:    misses,
	}
}

// ============================================================
//  后台清理
// ============================================================

// cleanupLoop 是后台 goroutine 的主循环
// 每隔 interval 触发一次过期清理
func (mc *MemCache) cleanupLoop(interval time.Duration) {
	defer mc.wg.Done() // 退出时通知 WaitGroup，解除 Close() 的阻塞

	// time.Ticker 会每隔 interval 向 ticker.C 发送当前的时间点
	ticker := time.NewTicker(interval)
	defer ticker.Stop() // 必须 Stop，否则 ticker 内部的 goroutine 会泄漏

	for {
		select {
		case <-ticker.C:
			// 定时器触发，执行一轮过期清理
			mc.deleteExpired()

		case <-mc.stopCh:
			// 收到停止信号
			// 知识点：close(ch) 是向所有监听者广播的惯用方式
			// 一个被关闭的 channel 会立即返回其类型的零值，且 ok=false
			slog.Info("[MemCache] 后台清理 goroutine 已推出")
			return
		}
	}
}

// deleteExpired 扫描并批量删除所有过期 key
// 策略：两阶段处理，最小化写锁持有时间
func (mc *MemCache) deleteExpired() {
	// === 第一阶段：读锁扫描，收集过期 key ===
	// 读锁期间，正常的 Get 不受影响（读锁可共享）
	mc.mu.RLock()
	var expiredKeys []string
	for k, ce := range mc.data {
		if ce.isExpired() {
			expiredKeys = append(expiredKeys, k)
		}
	}
	mc.mu.RUnlock()

	if len(expiredKeys) == 0 {
		return
	}

	// === 第二阶段：写锁批量删除 ===
	mc.mu.Lock()
	defer mc.mu.Unlock()
	for _, key := range expiredKeys {
		// 再次 double-check：两次加锁的间隙，该 key 可能被重新 Set
		if ce, ok := mc.data[key]; ok && ce.isExpired() {
			delete(mc.data, key)
		}
	}

	slog.Info("[MemCache] 本轮清理了过期 key", "expiredKeysNum", len(expiredKeys))
}

// Close 优雅关闭 MemCache
// 发送停止信号并等待后台 goroutine 完全退出，防止 goroutine 泄漏
func (mc *MemCache) Close() {
	// close(ch) 向所有监听 stopCh 的 goroutine 广播停止信号
	// ⚠️  注意：对同一个 channel close 两次会 panic，Close 只能调用一次
	close(mc.stopCh)
	mc.wg.Wait() // 阻塞直到所有后台 goroutine 调用了 wg.Done()
}

// ============================================================
//  主函数：演示各种特性
// ============================================================

func TestMemCache() {
	fmt.Println("========== MemCache 演示 ==========")

	// 创建缓存实例，每 2 秒自动清理一次
	cache := NewMemCache(2 * time.Second)
	defer cache.Close() // 程序退出时优雅关闭，确保后台 goroutine 不泄漏

	// --------------------------------------------------
	// 演示 1：基本的 Set 和 Get
	// --------------------------------------------------
	fmt.Println("\n--- 演示 1：基本操作 ---")
	cache.Set("name", "Alice", 0)                     // 永不过期
	cache.Set("session", "token-xyz", 3*time.Second)  // 3 秒后过期
	cache.Set("verify_code", "888888", 1*time.Second) // 1 秒后过期

	if v, ok := cache.Get("name"); ok {
		fmt.Printf("Get(name) = %v ✓\n", v)
	}
	if _, ok := cache.Get("not_exist"); !ok {
		fmt.Println("Get(not_exist) = 未命中 ✓")
	}

	// --------------------------------------------------
	// 演示 2：并发安全（10 个 goroutine 同时读写）
	// --------------------------------------------------
	fmt.Println("\n--- 演示 2：并发安全 ---")
	var wg sync.WaitGroup
	for i := 0; i < 10; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			key := fmt.Sprintf("worker-%d", id)
			cache.Set(key, id*100, 5*time.Second)
			if v, ok := cache.Get(key); ok {
				fmt.Printf("  goroutine-%d 写入并读取: %v\n", id, v)
			}
		}(i)
	}
	wg.Wait()
	fmt.Println("  10 个 goroutine 并发读写完成，无 panic ✓")

	// --------------------------------------------------
	// 演示 3：TTL 过期 + 惰性删除
	// --------------------------------------------------
	fmt.Println("\n--- 演示 3：TTL 过期 ---")
	fmt.Println("等待 1.5 秒...")
	time.Sleep(1500 * time.Millisecond)

	if _, ok := cache.Get("verify_code"); !ok {
		fmt.Println("verify_code 已过期（TTL=1s），Get 时触发惰性删除 ✓")
	}
	if v, ok := cache.Get("session"); ok {
		fmt.Printf("session 仍然有效（TTL=3s）: %v ✓\n", v)
	}

	// --------------------------------------------------
	// 演示 4：map 遍历顺序随机性
	// --------------------------------------------------
	fmt.Println("\n--- 演示 4：map 遍历顺序随机（每次输出可能不同）---")
	for i := 1; i <= 3; i++ {
		fmt.Printf("  第 %d 次 Keys(): %v\n", i, cache.Keys())
	}

	// --------------------------------------------------
	// 演示 5：Flush 清空（map 引用类型特性）
	// --------------------------------------------------
	fmt.Println("\n--- 演示 5：Flush ---")
	fmt.Printf("Flush 前有效 key 数: %d\n", cache.Stats().ValidKeys)
	cache.Flush()
	fmt.Printf("Flush 后有效 key 数: %d\n", cache.Stats().ValidKeys)

	// --------------------------------------------------
	// 演示 6：统计信息
	// --------------------------------------------------
	fmt.Println("\n--- 演示 6：Stats 统计 ---")
	cache.Set("foo", "bar", 10*time.Second)
	cache.Get("foo")   // hit
	cache.Get("foo")   // hit
	cache.Get("ghost") // miss
	cache.Get("ghost") // miss
	stats := cache.Stats()
	fmt.Printf("ValidKeys=%d  Hits=%d  Misses=%d\n",
		stats.ValidKeys, stats.Hits, stats.Misses)

	// --------------------------------------------------
	// 演示 7：nil map 陷阱演示（注释掉，仅作说明）
	// --------------------------------------------------
	// var nilMap map[string]int
	// fmt.Println(nilMap["key"]) // ✓ 读取 nil map 返回零值，不 panic
	// nilMap["key"] = 1          // ✗ 写入 nil map 会 panic！
	// delete(nilMap, "key")      // ✗ delete nil map 也会 panic！

	fmt.Println("\n========== 演示结束 ==========")
}
