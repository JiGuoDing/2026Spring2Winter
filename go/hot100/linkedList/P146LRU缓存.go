package linkedList

// 双向链表节点
type Entry struct {
	key        int
	value      int
	prev, next *Entry
}

// LRU 缓存
type LRUCache struct {
	// 容量
	capacity int
	// 底层存储
	data map[int]*Entry
	// 虚拟头尾节点
	head, tail *Entry
}

func Constructor(capacity int) LRUCache {
	head, tail := &Entry{}, &Entry{}
	head.next = tail
	tail.prev = head
	return LRUCache{
		capacity: capacity,
		data:     make(map[int]*Entry),
		head:     head,
		tail:     tail,
	}
}

// * 链表操作
// 将 entry 从链表中移除
func (this *LRUCache) removeEntry(entry *Entry) {
	entry.prev.next = entry.next
	entry.next.prev = entry.prev
}

// 将节点插入到 head 之后 (标记为最近使用)
func (this *LRUCache) addToFront(entry *Entry) {
	entry.next = this.head.next
	entry.prev = this.head
	this.head.next.prev = entry
	this.head.next = entry
}

// 将已存在的节点移动到头部
func (this *LRUCache) moveToFront(entry *Entry) {
	this.removeEntry(entry)
	this.addToFront(entry)
}

// 移除尾部节点 (最久未使用)
func (this *LRUCache) removeTail() {
	entry := this.tail.prev
	this.removeEntry(entry)
	delete(this.data, entry.key)
}

func (this *LRUCache) Get(key int) int {
	if entry, ok := this.data[key]; ok {
		this.moveToFront(entry)
		return entry.value
	}
	// 没有该键
	return -1
}

func (this *LRUCache) Put(key int, value int) {
	if entry, ok := this.data[key]; ok {
		// 该 key 已存在，更新值并移动到头部
		entry.value = value
		this.moveToFront(entry)
	} else {
		// 该 key 不存在，新建节点并插入头部
		newEntry := &Entry{
			key:   key,
			value: value,
		}
		this.data[key] = newEntry
		this.addToFront(newEntry)

		if len(this.data) > this.capacity {
			this.removeTail()
		}
	}
}
