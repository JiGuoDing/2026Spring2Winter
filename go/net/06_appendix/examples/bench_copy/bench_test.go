package benchcopy

import (
	"bytes"
	"io"
	"strings"
	"testing"
)

func BenchmarkIOCopyWriteTo(b *testing.B) {
	payload := strings.Repeat("a", 4*1024)
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		src := strings.NewReader(payload)
		dst := &bytes.Buffer{}
		if _, err := io.Copy(dst, src); err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkIOCopyBuffer(b *testing.B) {
	payload := strings.Repeat("a", 4*1024)
	buffer := make([]byte, 32*1024)
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		src := strings.NewReader(payload)
		dst := &bytes.Buffer{}
		if _, err := io.CopyBuffer(dst, src, buffer); err != nil {
			b.Fatal(err)
		}
	}
}
