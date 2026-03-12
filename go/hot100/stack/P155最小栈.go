package stack

/*
使用两个栈：
    主栈 (stack)：存储所有正常 Push 进来的元素。
    辅助栈 (minStack)：专门存储当前的“最小值”。
        当 Push 一个新元素 val 时，如果 val 小于或等于 minStack 的栈顶元素（或者 minStack 为空），则将 val 也 Push 进 minStack。
        当 Pop 主栈元素时，如果弹出的元素等于 minStack 的栈顶元素，则 minStack 也要同时 Pop。
        这样，minStack 的栈顶永远是目前主栈中的最小值。
*/

type MinStack struct {
	stack    []int
	minStack []int
}

func Constructor() MinStack {
	return MinStack{
		stack:    make([]int, 0),
		minStack: make([]int, 0),
	}
}

func (this *MinStack) Push(val int) {
	// 首先压入主栈
	this.stack = append(this.stack, val)

	if len(this.minStack) == 0 || val <= this.minStack[len(this.minStack)-1] {
		this.minStack = append(this.minStack, val)
	}
}

func (this *MinStack) Pop() {
	// 处理边界情况
	if len(this.stack) == 0 {
		return
	}

	// 获取即将弹出的主栈栈顶元素
	topVal := this.stack[len(this.stack)-1]
	// 主栈弹出栈顶元素
	this.stack = this.stack[:len(this.stack)-1]

	// 判断辅助栈是否要弹出栈顶元素
	if topVal == this.minStack[len(this.minStack)-1] {
		this.minStack = this.minStack[:len(this.minStack)-1]
	}
}

func (this *MinStack) Top() int {
	if len(this.stack) == 0 {
		return -1
	}

	return this.stack[len(this.stack)-1]
}

func (this *MinStack) GetMin() int {
	if len(this.minStack) == 0 {
		return -1
	}

	return this.minStack[len(this.minStack)-1]
}

/**
 * Your MinStack object will be instantiated and called as such:
 * obj := Constructor();
 * obj.Push(val);
 * obj.Pop();
 * param_3 := obj.Top();
 * param_4 := obj.GetMin();
 */
