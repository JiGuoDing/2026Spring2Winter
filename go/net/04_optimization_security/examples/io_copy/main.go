package main

import (
	"bytes"
	"fmt"
	"io"
	"log"
	"strings"
)

type fastReader struct {
	reader *strings.Reader
}

func (r *fastReader) Read(p []byte) (int, error) {
	return r.reader.Read(p)
}

func (r *fastReader) WriteTo(w io.Writer) (int64, error) {
	fmt.Println("source WriteTo fast path used")
	return r.reader.WriteTo(w)
}

type plainReader struct {
	data   []byte
	offset int
}

func (r *plainReader) Read(p []byte) (int, error) {
	if r.offset >= len(r.data) {
		return 0, io.EOF
	}
	n := copy(p, r.data[r.offset:])
	r.offset += n
	return n, nil
}

type loggingBuffer struct {
	bytes.Buffer
}

func (b *loggingBuffer) ReadFrom(r io.Reader) (int64, error) {
	fmt.Println("destination ReadFrom fast path used")
	return b.Buffer.ReadFrom(r)
}

func main() {
	firstSource := &fastReader{reader: strings.NewReader("copy via WriteTo\n")}
	firstDestination := &bytes.Buffer{}
	copied1, err := io.Copy(firstDestination, firstSource)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Printf("copy #1 bytes=%d body=%q\n", copied1, firstDestination.String())

	secondSource := &plainReader{data: []byte("copy via ReadFrom\n")}
	secondDestination := &loggingBuffer{}
	copied2, err := io.Copy(secondDestination, secondSource)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Printf("copy #2 bytes=%d body=%q\n", copied2, secondDestination.String())
}
