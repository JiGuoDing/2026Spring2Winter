class Entry:
    def __init__(self, key: int, value: int):
        self.key = key
        self.value = value
        self.prev = None
        self.next = None
    
class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.data = {}
        self.head = Entry(-1, -1)
        self.tail = Entry(-1, -1)
        self.head.next = self.tail
        self.tail.prev = self.head
        
    def put(self, key: int, value: int) -> None:
        if key in self.data:
            self.data[key] = value
            self.moveToFront(self.data[key])
        else:
            new_entry = Entry(key=key, value=value)
            if len(self.data) >= self.capacity:
                self.removeTail()
            self.addToFront(new_entry)
            self.data[key] = new_entry
            
    
    def get(self, key: int) -> int:
        if key in self.data:
            val = self.data[key].value
            print(val)
            self.moveToFront(self.data[key])
            return val
        else:
            print(-1)
            return -1
    
    def removeEntry(self, entry: Entry) -> None:
        entry.prev.next = entry.next
        entry.next.prev = entry.prev
        
    def addToFront(self, entry: Entry) -> None:
        entry.prev = self.head
        entry.next = self.head.next
        self.head.next.prev = entry
        self.head.next = entry
        
    def moveToFront(self, entry: Entry) -> None:
        self.removeEntry(entry=entry)
        self.addToFront(entry=entry)
        
    def removeTail(self) -> None:
        entry = self.tail.prev
        if entry is not self.head:
            self.removeEntry(entry=entry)
            del self.data[entry.key]
            
if __name__ == "__main__":
    lru = LRUCache(capacity=3)
    # print(repr(lru))
    lru.put(1, 1)
    # 1
    lru.put(2, 2)
    # 2, 1
    lru.put(3, 3)
    # 3, 2, 1
    lru.get(2)
    # 2, 3, 1
    lru.put(4, 4)
    # 4, 2, 3
    lru.get(1)
    # 4, 2, 3
    lru.put(1,1)
    # 1, 4, 2
    lru.get(3)
    # 1, 4, 2
    lru.get(4)