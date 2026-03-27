package binarySearch

func findMin(nums []int) int {
	// 找到划分点，将切片划分为两个升序的子切片
	spinPosition := binarySearchSpin(nums)
	return nums[(spinPosition+1)%len(nums)]
}
