# Golang 面试题

## 1. 基础面试题

### 1.1 协程和线程和进程的区别

- 进程：进程是具有一定独立功能的程序，进程是系统资源分配和调度的最小单位。每个进程有自己的独立内存空间，不同进程通过进程间通信来通信。由于进程比较重量，占据独立的内存，所以上下文进程间的切换开销 (栈、寄存器、虚拟内存、文件句柄等) 比较大，但相对比较稳定安全。
- 线程：线程是进程的一个实体，线程是内核态，而且是 CPU 调度和分派的基本单位，它是比进程更小的能独立运行的基本单位。线程间通信主要通过共享内存，上下文切换很快，资源开销较小，但相比进程不够稳定且容易丢失数据。
- 协程：协程是一种用户态的轻量级线程，协程的调度完全由用户来控制。协程拥有自己的寄存器上下文和栈。协程调度切换时，将寄存器上下文和栈保存到其他地方，在切回来的时候，恢复先前保存的寄存器上下文和栈，直接操作栈则基本没有内核切换的开销，可以不加锁地访问全局变量，所以上下文的切换非常快。

### 1.4 Golang 中 make 和 new 的区别

- make:
  - 用于初始化并分配内存，只能用于创建 `slice`, `map` 和 `channel` 三种类型
  - 返回的是初始化后的数据结构，而不是指针
- new:
  - 用于分配内存，但不初始化，返回的是指向该内存的指针
  - 可以用于任何类型的内存分配

make 函数创建的是数据结构 (slice, map, channel) 本身，且返回初始化后的值。而 new 函数创建的是可以指向任意类型的指针，返回指向未初始化零值的内存地址。

### 1.7 如何高效地拼接字符串

拼接字符串的方式有：

- `+`
- fmt.Sprintf
- strings.Builder
  - 用 WriteString() 进行拼接，内部实现是指针+切片，同时 String() 返回拼接后的字符串，它是直接把 []byte 转换为 string，从而避免变量拷贝。
  - var sb strings.Builder
- bytes.Buffer
- strings.Join

### 1.8 defer 的执行顺序是怎样的？defer 的作用或者使用场景是什么

defer 执行顺序和调用顺序相反，类似于栈的后进先出 (LIFO)

defer 的作用是：当 defer 语句被执行时，跟在 defer 后的函数会被延迟执行。直到包含该 defer 语句的函数执行完毕时，defer 后的函数才会被执行，不论包含 defer 语句的函数是通过 return 正常结束，还是由于 panic 导致的异常结束。可以在一个函数中执行多条 defer 语句，它们的执行顺序与声明顺序相反。

defer 的常用场景：

- defer 语句常用语处理成对的操作，如打开、关闭、链接、断开连接、加锁和释放锁
- 通过 defer 机制，不论函数逻辑多复杂，都能保证在任何执行路径下，资源被释放
- 释放资源的 defer 应当直接跟在请求资源的语句后

### 1.10 Go 语言 tag 有什么用

tag 可以为结构体成员提供属性

- json 序列化或反序列化时字段的名称
- db: sqlx 模块中对应的数据库字段名
- form: gin 框架中对应的前端的数据字段名
- binding: 搭配 form 使用，默认如果没查找到结构体中的某个字段则不报错值为空，bingding 为 required 代表没找到返回错误给前端

### 1.11 Go 打印时 %v %+v %#v 的区别

- %v 只输出所有的值
- %+v 先输出字段名字，再输出该字段的值
- %#v 先输出结构体名字值，在输出结构体 (字段名 + 字段值)

### 1.13 Go 语言中，空 struct{} 用什么用？

空struct{}不占用任何空间

- 用 map 模拟一个 set，那么就要把值置为 struct{}，struct{} 本身不占任何空间，可以避免任何多余的内存分配
  - 例如对于一个名为 set 的 map，set["apple"] = struct{}{}
- 有时候给通道发送一个空结构体 channel <- struct{}{}，可以节省空间

### 1.14 init() 函数是什么时候执行的？

init() 函数在 main 函数之前执行

init() 函数是 go 初始化的一部分，由 runtime 初始化每个导入的包，初始化不是按照从上到下的导入顺序，而是按照解析的依赖关系，没有依赖的包最先初始化

每个包首先初始化包作用域的常量和变量 (常量优先于变量)，然后执行包的 init() 函数。同一个包，甚至是同一个源文件可以有多个 init() 函数。init() 函数没有参数和返回值，不能被其他函数调用，同一个包内多个 init() 函数的执行顺序不做保证

执行顺序：import -> const -> var -> init() -> main()

![init_sequence](./assets/init_sequence.png "init_sequence")

### 1.17 Go 函数传参是值类型还是引用类型？

- 在 Go 语言中只存在值传递，要么是值的副本，要么是指针的副本。无论是值类型的变量还是引用类型的变量亦或是指针类型的变量作为参数传递都会发生值拷贝，开辟新的内存空间
- 另外值传递、引用传递和值类型、引用类型是两个不同的概念。引用类型作为变量传递可以影响到函数外部是因为发生值拷贝后新旧变量指向了相同的内存地址
- map 和 channel 是引用类型 (底层是指针结构)
  - 传递的是 map 或 channel 的描述符 (类似指针) 的副本，但它们仍指向同一个底层数据结构

### 1.18 如何知道一个对象是分配在栈上还是堆上？

Go 和 C++ 不同，Go 局部变量会进行逃逸分析，如果变量离开作用域后没有被引用，则优先分配到栈上，否则分配到堆上

如何判断是否发生了逃逸 (escape) ？

```sh
go build -gcflags '-m -m -l' xxx.go 
```

关于逃逸的可能情况：变量大小不确定，变量类型不确定，变量分配的内存超过用户栈最大值，暴露给了外部指针

### 1.19 Go 的多返回值是如何实现的？

Go 的多返回值是通过在函数调用栈帧上预留空间并进行值复制来实现的。在函数调用发生时，Go 编译器会计算出函数所有返回值的总大小。在为该函数创建栈帧时，就会在调用方 (caller) 的栈帧上，为这些返回值预留出连续的内存空间

当函数执行到 return 语句时，它会将其要返回的各个值复制到这些预留好的栈空间中。函数执行完毕后，控制权返回给调用方。此时，调用方可以直接从它自己的栈帧上 (即之前为返回值预留的空间) 获取这些返回的值

### 1.21 Go 普通指针和 unsafe.Pointer 有什么区别？

普通指针比如 *int，*string，他们有明确的类型信息，编译器会进行类型检查和垃圾回收跟踪。不同类型的指针之间不能直接转换，这是 Go 类型安全的体现

unsafe.Pointer 是 Go 的通用指针类型，可以理解为 C 的 void *，它绕过了 Go 的类型系统，unsafe.Pointer 可以与任意类型的指针相互转换，也可以与 uintptr 进行转换来做指针运算

另外，普通指针受 GC 管理和类型约束，unsafe.Pointer 不受类型约束但仍受 GC 跟踪

### 1.22 unsafe.Pointer 和 uintptr 有什么区别？

unsafe.Pointer 和 uintptr 可以相互转换，这是 Go 提供的唯一合法的指针运算方式。典型用法是先将 unsafe.Pointer 转换为 uintptr 做算术运算，然后再转回 unsafe.Pointer 使用

最关键的区别在于 GC 追踪，unsafe.Pointer 会被垃圾回收器追踪，它指向的内存不会被错误回收。而 uintptr 只是一个普通整数，GC 完全不知道它指向什么，如果没有其他引用，对应内存可能随时被回收。

unsafe.Pointer 有 GC 保护，uintptr 没有，这是它们最本质的区别。

## 2. Slice 面试题

### 2.1 slice 的底层结构是怎样的？

slice 的底层数据结构也是数组，slice 是对数组的封装，它描述一个数组的片段。slice 实际上是一个结构体，包含三个字段

- 长度
- 容量
- 底层数组

```go
type slice struct {
  // 元素指针
  array unsafe.Pointer
  // 长度
  len int
  // 容量
  cap int
}
```

### 2.3 从一个切片截取出另一个切片，修改新切片的值是否会影响原来的切片内容？

在截取完之后，如果新切片没有触发扩容，则修改切片元素会影响原切片，如果触发了扩容则不会

在 Go 1.18及之后，引入了新的扩容规则

当原 slice 容量 (oldcap) 小于 256 时，新 slice (newcap) 容量为原来的 2 倍；原 slice 容量超过 256，新 slice 容量 newcap = oldcap + (oldcap + 3 * 256) / 4

## 3. Map 面试题

### 3.1 Go Map 的底层实现原理

map 是一个 hmap 结构，Go Map 的底层实现是一个哈希表，它在运行时表现为一个指向 hmap 结构体的指针，hmap 中记录了通数组指针 buckets、溢出桶指针以及元素个数等字段。每个桶是一个 bmap 结构体，能存储 8 个键值对和 8 个 tophash，并有指向下一个溢出桶的指针 overflow。为了内存紧凑，bmap 中采用的是先存 8 个键再存 8 个值的存储方式

```go
type hmap struct {
  // map 中元素的个数
  count int
  // 状态标志位，记录 map 的状态
  flags uint8
  // 桶数以 2 为底的对数，决定了哈希表的大小，即 B = log_2(len(buckets))，比如 B = 3，那么桶的数量为 2^3 = 8
  B uint8
  // 溢出桶的数量的近似值
  noverflow uint16
  // 哈希种子，用于计算哈希值
  hash0 uint32

  // 指向 buckets 数组的指针，buckets 数组的大小为 2^B，每个桶存储 8 个键值对
  buckets unsafe.Pointer
  // 一个指向 buckets 数组的指针，在扩容时，oldbuckets 指向老的 buckets 数组 (大小为新buckets数组的一半)，非扩容时，oldbuckets 为空
  oldbuckets unsafe.Pointer
  // 表示扩容进度的计数器，小于该值的桶已经完成迁移
  nevacuate uintptr

  // 指向 mapextra 结构体的指针，mapextra 存储 map 中的溢出桶
  extra *mapextra
}
```

![hmap_struct](./assets/hmap_struct.png "hmap_struct")

![bmap_struct](./assets/bmap_struct.png "bmap_struct")

### 3.2 Go Map 的遍历是有序的还是无序的？

Go Map 的遍历是 **完全随机** 的，没有固定的顺序。map 每次遍历，都会从一个随机值序号的桶，在每个桶中，再从按照之前选定随机槽位开始遍历，所以是无序的

这意味着当使用 for range 遍历一个 Map 时，每次运行得到的元素顺序可能都不一样，甚至在同一个程序运行时多次遍历同一个 Map，顺序也可能不同。

但是使用 fmt.Println 打印 Map 时，元素顺序是固定的，因为 fmt.Println 会按照键的哈希值升序排序输出

### 3.4 Map 如何实现顺序读取？

如果业务上确实需要有序遍历，最规范的做法就是将 Map 的键 (Key) 取出来放入一个切片 (Slice) 中，用 sort 包对切片进行排序，然后根据这个有序的切片去遍历 Map

```go
package main

import (
   "fmt"
   "sort"
)

func main() {
   keyList := make([]int, 0)
   m := map[int]int{
      3: 200,
      4: 200,
      1: 100,
      8: 800,
      5: 500,
      2: 200,
   }
   for key := range m {
      keyList = append(keyList, key)
   }
   sort.Ints(keyList)
   for _, key := range keyList {
      fmt.Println(key, m[key])
   }
}
```

### 3.5 Go Map 是否是并发安全的？

Go Map 不是并发安全的，并发读写 Map 会导致数据竞争和不一致的结果。如果需要在并发场景下使用 Map，需要使用 sync.Map 或者其他并发安全的 Map 实现

### 3.7 Go Map 的扩容时机是怎样的？

向 map 插入新 key 时，会进行条件检测，符合以下两个条件，就会触发扩容

- 装载因子 (元素个数与桶数的比值) 超过阈值，源码中定义的阈值是 6.5，此时会触发双倍扩容，即 B+1，桶数会增加一倍
- overflow 的 bucket 数量过多
  - 当 B < 15 时，overflow bucket 数量超过 2^B
  - 当 B >= 15 时，overflow bucket 数量超过 2^15

这两种情况下会触发等量扩容，B 不变，创建一组新 bucket (数量和原来一样)，将原有的元素搬迁到新 bucket 中

### 3.8 Go Map 的扩容过程是怎样的？

Go Map 的扩容是 **渐进式** 的 (gradual)，首先分配新空间，然后在后续的每一次插入、修改或删除操作时，才会顺便搬迁一两个旧桶的数据

如果是触发双倍扩容，会新建一个 buckets 数组，新的 buckets 数量大小是原来的 2 倍，然后旧 buckets 数据搬迁到新的 buckets。如果是等量扩容，buckets 数量维持不变，重新做一遍类似双倍扩容的搬迁动作，把松散的键值对重新排列一次，使得同一个 bucket 中的 key 排列地更紧密，这样节省空间，存取效率更高

### 3.9 可以对 Map 的元素取地址吗？

无法对 map 的 key 或 value 进行取址，会发生编译报错，这样设计主要是因为 map 一旦发生扩容，key 和 value 的位置就会改变，之前保存的地址也就失效了

### 3.10 Map 中删除一个 key，它的内存会释放吗？

delete 一个 key，并不会立即释放或收缩 Map 占用的内存，具体来说，delete(m, key) 只是把 key 和 value 对应的内存块标记为 "空闲"，让它们的内容可以被后续的 GC 处理掉。但是，Map 底层为了存储这些键值对二分配的 "桶" 数组，它的规模时不会缩小的，只有在置空这个 map 的时候，整个 map 的空间才会被垃圾回收释放

![map_delete_key](./assets/map_delete_key.png "map_delete_key")

## 4. Channel 面试题

### 4.1 什么是 CSP？

CSP (Communicating Sequential Processes，通信顺序进程) 并发编程模型，它的核心思想是：通过通信共享内存，而不是通过共享内存来通信。Go 语言的 Goroutine 和 Channel 机制，就是 CSP 的经典实现，具有以下特点：

- 避免共享内存：协程 (Goroutine) 不直接修改变量，而是通过 Channel 通信
- 天然同步：Channel 的发送 / 接受自带同步机制，无需手动加锁
- 易于组合：Channel 可以嵌套使用，构建复杂并发模式 (如管道、超时控制)

### 4.2 Channel 的底层实现原理是怎样的？

Channel 的底层是一个名为 `hchan` 的结构体，核心包含几个关键组件：

- `环形缓冲区`：有缓冲 channel 内部维护一个固定大小的环形队列，用 buf 指针指向缓冲区，sendx 和 recvx 分别记录发送和接收的位置索引
- `两个等待队列`：sendq 和 recvq 用来管理阻塞的 goroutine。sendq 存储因 channel 满而阻塞的发送者，recvq 存储因 channel 空而阻塞的接收者。这些队列用双向链表实现，当条件满足时会唤醒对应的 goroutine
- `互斥锁`：hchan 内部有一个 mutex，所有的发送、接收操作都需要先获取锁，用来保证并发安全

```go
type hchan struct {
  qcount   uint           // 队列中元素的数量
  dataqsiz uint           // 环形队列的长度
  buf      unsafe.Pointer // 指向环形队列的指针
  elemsize uint16         // 每个元素的大小
  closed   uint32         // 通道是否关闭
  elemtype *_type         // 元素的类型
  sendx    uint           // 发送索引
  recvx    uint           // 接收索引
  recvq    waitq          // 接收等待队列，等待接收的 goroutine 队列
  sendq    waitq          // 发送等待队列，等待发送的 goroutine 队列
  lock     mutex          // 互斥锁
}
```

![channel_hchan](./assets/channel_hchan.png "channel_hchan")

### 4.3 向 channel 发送数据的过程是怎样的？

向 channel 发送数据的整个过程都会在 mutex 保护下进行，保证并发安全

1. 首先检查是否有等待的接收者，如果 recvq 队列非空，说明有 goroutine 在等待接收数据，这时会直接把数据传递给等待的接收者，跳过缓冲区。同时会唤醒对应的 goroutine 继续执行
2. 如果没有等待的接收者，就尝试写入缓冲区。检查缓冲区是否还有空间，如果 qcount < dataqsize，就把数据复制到 buf[sendx]，然后更新 sendx 索引和 qcount 计数
3. 当缓冲区满了就需要阻塞等待。创建一个 sudog (pseudo goroutine) 结构体包装当前 goroutine 和要发送的数据，加入到 sendq 等待队列中，然后调用 gopark 让当前 goroutine 进入阻塞状态，让出 CPU 给其他 goroutine

被唤醒后继续执行。当有接收者从 channel 读取数据后，会从 sendq 中唤醒一个等待的发送者，被唤醒的 goroutine 会完成数据发送并继续执行

有两个 receiver 在 channel 的一边虎视眈眈地等着，这时 channel 另一边来了一个 sender 准备向 channel 发送数据，为了高效，用不着通过 channel 的 buf "中转"一次，直接从源地址把数据 copy 到目的地址就可以了，效率高啊！

### 4.4 从 channel 读取数据的过程是怎样的？

1. 首先检查是否有等待的发送者，如果 sendq 队列非空，说明有 goroutine 在等待发送数据。对于无缓冲 channel，会直接从发送者那里接收数据；对于有缓冲 channel，会先从缓冲区读取数据，然后把等待的发送者的数据放入缓冲区，这样保持 FIFO 顺序
2. 如果没有等待发送者，尝试从缓冲区读取，检查 qcount > 0，如果缓冲区有数据，就从 buf[recvx] 位置取出数据，然后更新 recvx 索引和 qcount 计数。这是缓冲区有数据时的正常路径

缓冲区为空时需要阻塞等待，创建 sudog 结构体包装当前 goroutine，加入到 recvq 等待队列，调用 gopark 进入阻塞状态，当有发送者写入数据时会被唤醒继续执行

从已关闭的 channel 读取时有特殊处理，如果 channel 已关闭且缓冲区为空，会返回零值和 false 标志；如果缓冲区还有数据，可以正常读取直到清空。这就是为什么 v, ok := <-ch 会返回两个值，第一个是 channel 中的数据，第二个是一个布尔值，表示 channel 是否已关闭

### 4.6 Channel 在什么情况下会引起内存泄漏？

Channel 引起内存泄漏最常见的是引起 goroutine 泄漏从而导致的间接内存泄漏，当 goroutine 阻塞在 channel 操作上永远无法退出时，goroutine 本身和它引用的变量都无法被 GC 回收。例如当一个 goroutine 在等待接收数据，但发送者已经退出了，这个接收者就会永远阻塞下去。或者 select 语句使用不当，在没有 default 分支的 select 中，如果所有 case 都无法执行，goroutine 会永远阻塞，出现内存泄漏

### 4.7 关闭 channel 会产生异常吗？

试图重复关闭一个 channel、关闭一个 nil 值的 channe、关闭一个只有接收方向的 channel 都将导致 panic 异常

### 4.9 什么是 select？

select 是 Go 专门为 channel 操作设计的多路复用控制结构，类似于网络编程中的 select 系统调用

核心作用是同时监听多个 channel 操作，当有多个 channel 都可能有数据收发时，select 能够选择其中一个可执行的 case 进行操作，而不是按顺序逐个尝试。例如同时监听数据输入、超时信号、取消信号等

### 4.10 select 的执行机制是怎样的？

select 的执行机制是随机选择，如果多个 case 同时满足条件，Go 会随机选择一个执行，这避免了饥饿问题，如果没有 case 能执行就会执行 default，当前 goroutine 会阻塞等待

### 4.11 select 的实现原理是怎样的？

Go 实现 select 时，定义了一个数据结构 scase，表示每个 case 语句 (包含 default)，scase 结构包含 channel 指针、操作类型等信息，select 操作的整个过程通过 selectgo 函数在 runtime 层面实现

Go 运行时会将所有 case 进行随机排序，这是为了避免饥饿问题。然后执行两轮扫描策略：第一轮直接检查每个 channel 是否可读写，如果找到就绪的立即执行；如果都没就绪，第二轮就把当前 goroutine 加入到所有 channel 的发送或接收队列中，然后调用 gopark 进入睡眠状态，使当前 goroutine 让出 CPU

当某个 channel 变为可操作时，调度器会唤醒对应的 goroutine，此时需要从其他 channel 的等待队列中清理掉这个 goroutine，然后执行对应的 case 分支

核心原理：case 随机化 + 双重循环检测

```go
type scase struct {
    c *hchan // 关联的 channel 指针
    elem unsafe.Pointer // 数据元素指针，用于存储接收或发送的数据
    kind uint16 // case 类型：caseNil, caseRecv, caseSend, caseDefault
    pc uintptr // 程序计数器，用于调试
    releasetime int64 // 释放时间，用于竞态检测
}
```

![select_case](./assets/select_case.png "select_case")

在默认的情况下，select 语句会在编译阶段经过如下过程的处理：

1. 将所有的 case 转换成包含 Channel 以及类型等信息的 scase 结构体；

2. 调用运行时函数 selectgo 获取被选择的 scase 结构体索引，如果当前的 scase 是一个接收数据的操作，还会返回一个指示当前 case 是否是接收的布尔值；

3. 通过 for 循环生成一组 if 语句，在语句中判断自己是不是被选中的 case。
