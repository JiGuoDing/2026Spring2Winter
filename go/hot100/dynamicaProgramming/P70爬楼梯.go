package dynamicaprogramming

func climbStairs(n int) int {
	a, b, r := 0, 0, 1
	for i := 1; i <= n; i++ {
		a = b
		b = r
		r = a + b
	}
	return r
}
