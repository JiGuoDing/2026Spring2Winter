package heap

type element struct {
	val       int
	frequency int
}

// 统计出现频率最高的元素的最大堆
type FrequentHeap struct {
	data []element
	size int
}

// 创建一个空的统计频率的堆
func NewFrequentHeap() *FrequentHeap {
	return &FrequentHeap{
		data: []element{},
		size: 0,
	}
}

func (frequentHeap *FrequentHeap) Len() int {
	return frequentHeap.size
}

func (frequentHeap *FrequentHeap) Top() element {
	return frequentHeap.data[0]
}

func (frequentHeap *FrequentHeap) Pop() element {
	top := frequentHeap.data[0]
	frequentHeap.size--
	if frequentHeap.size > 0 {
		frequentHeap.data[0] = frequentHeap.data[frequentHeap.size]
		frequentHeap.data = frequentHeap.data[:frequentHeap.size]
		frequentHeap.siftDown(0)
	} else {
		frequentHeap.data = []element{}
	}

	return top
}

func (frequentHeap *FrequentHeap) Push(ele element) {
	for i := 0; i < frequentHeap.size; i++ {
		if frequentHeap.data[i].val == ele.val {
			frequentHeap.data[i].frequency += ele.frequency
			frequentHeap.siftUp(i)
			return
		}
	}
	frequentHeap.data = append(frequentHeap.data, ele)
	frequentHeap.size++
	frequentHeap.siftUp(frequentHeap.size - 1)
}

func (frequentHeap *FrequentHeap) siftUp(index int) {
	for index > 0 {
		parent := (index - 1) / 2
		if frequentHeap.data[index].frequency > frequentHeap.data[parent].frequency {
			frequentHeap.data[index], frequentHeap.data[parent] = frequentHeap.data[parent], frequentHeap.data[index]
			index = parent
		} else {
			break
		}
	}
}

func (frequentHeap *FrequentHeap) siftDown(index int) {
	for {
		biggest := index
		left, right := 2*index+1, 2*index+2
		if left < frequentHeap.size && frequentHeap.data[biggest].frequency < frequentHeap.data[left].frequency {
			biggest = left
		}
		if right < frequentHeap.size && frequentHeap.data[biggest].frequency < frequentHeap.data[right].frequency {
			biggest = right
		}

		if biggest == index {
			break
		}

		frequentHeap.data[biggest], frequentHeap.data[index] = frequentHeap.data[index], frequentHeap.data[biggest]
		index = biggest
	}
}

func topKFrequent(nums []int, k int) []int {
	fh := NewFrequentHeap()
	for _, num := range nums {
		fh.Push(element{
			val:       num,
			frequency: 1,
		})
	}
	res := make([]int, 0)
	for i := 0; i < k; i++ {
		res = append(res, fh.Pop().val)
	}
	return res
}
