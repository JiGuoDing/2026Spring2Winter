package utils

import (
	"bufio"
	"fmt"
	"os"
)

type FastScanner struct {
	r *bufio.Reader
}

func NewFastScanner() *FastScanner {
	// 1<<20 = 1MB 缓冲，一般足够
	return &FastScanner{r: bufio.NewReaderSize(os.Stdin, 1<<20)}
}

// 读下一个非空白字符，返回该字符
func (fs *FastScanner) nextNonSpace() byte {
	for {
		b, err := fs.r.ReadByte()
		if err != nil {
			return 0
		}
		if b > ' ' { // 非空白（空格/换行/制表符等）
			return b
		}
	}
}

// NextInt 读取一个 int（支持负数）
func (fs *FastScanner) NextInt() int {
	sign := 1
	b := fs.nextNonSpace()
	if b == '-' {
		sign = -1
		b, _ = fs.r.ReadByte()
	}
	n := 0
	for b > ' ' {
		n = n*10 + int(b-'0')
		b2, err := fs.r.ReadByte()
		if err != nil {
			break
		}
		b = b2
	}
	return sign * n
}

// NextInt64 读取 int64（支持负数）
func (fs *FastScanner) NextInt64() int64 {
	sign := int64(1)
	b := fs.nextNonSpace()
	if b == '-' {
		sign = -1
		b, _ = fs.r.ReadByte()
	}
	var n int64
	for b > ' ' {
		n = n*10 + int64(b-'0')
		b2, err := fs.r.ReadByte()
		if err != nil {
			break
		}
		b = b2
	}
	return sign * n
}

// NextFloat64 读取 float64（支持：-12.34 这种；不处理科学计数法）
func (fs *FastScanner) NextFloat64() float64 {
	sign := 1.0
	b := fs.nextNonSpace()
	if b == '-' {
		sign = -1
		b, _ = fs.r.ReadByte()
	}

	// 整数部分
	val := 0.0
	for b >= '0' && b <= '9' {
		val = val*10 + float64(b-'0')
		b2, err := fs.r.ReadByte()
		if err != nil {
			return sign * val
		}
		b = b2
	}

	// 小数部分
	if b == '.' {
		base := 0.1
		b2, err := fs.r.ReadByte()
		if err != nil {
			return sign * val
		}
		b = b2
		for b >= '0' && b <= '9' {
			val += float64(b-'0') * base
			base *= 0.1
			b3, err := fs.r.ReadByte()
			if err != nil {
				break
			}
			b = b3
		}
	}

	// 已读到空白或其它字符，直接返回
	return sign * val
}

func scannerHelper() {
	fs := NewFastScanner()
	out := bufio.NewWriterSize(os.Stdout, 1<<20)
	defer out.Flush()

	// ====== 使用示例：第一行两个整数，后续 N 行每行两个整数 ======
	N := fs.NextInt()
	T := fs.NextInt()

	_ = T
	for i := 0; i < N; i++ {
		a := fs.NextInt()
		b := fs.NextInt()
		_, _ = a, b
	}

	fmt.Fprintln(out, "ok") // 示例输出
}
