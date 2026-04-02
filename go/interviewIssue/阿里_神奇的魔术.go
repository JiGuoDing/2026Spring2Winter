package interviewIssue

import (
	"bufio"
	"fmt"
	"os"
)

func Magic() {
	reader, writer := bufio.NewReaderSize(os.Stdin, 1<<20), bufio.NewWriterSize(os.Stdout, 1<<20)
	defer writer.Flush()
	var T int
	fmt.Fscan(reader, &T)

	for ; T > 0; T-- {
		var x int
		fmt.Fscan(reader, &x)
		if x < 2 {
			fmt.Fprintln(writer, 2)
			continue
		}
		if isPrime(x) {
			fmt.Fprintln(writer, x)
			continue
		}
		foundLarger, foundSmaller := make(chan int), make(chan int)
		go func() {
			for i := x + 1; ; i++ {
				if isPrime(i) {
					foundLarger <- i
					return
				}
			}
		}()
		go func() {
			for i := x - 1; i >= 2; i-- {
				if isPrime(i) {
					foundSmaller <- i
					return
				}
			}
		}()
		larger, smaller := <-foundLarger, <-foundSmaller
		if larger-x == x-smaller {
			fmt.Fprintln(writer, min(larger, smaller))
		} else if larger-x < x-smaller {

			fmt.Fprintln(writer, larger)
		} else {
			fmt.Fprintln(writer, smaller)
		}
	}
}

// 判断一个数是否为质数
func isPrime(num int) bool {
	if num < 2 {
		return false
	}
	for i := 2; i*i <= num; i++ {
		if num%i == 0 {
			return false
		}
	}
	return true
}
