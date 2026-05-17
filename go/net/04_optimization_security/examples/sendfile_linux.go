//go:build linux

package main

import (
	"fmt"
	"io"
	"log"
	"net"
	"os"
	"sync"
	"syscall"
)

func main() {
	const content = "sendfile demo line 1\nsendfile demo line 2\n"

	tempFile, err := os.CreateTemp("", "sendfile-demo-*.txt")
	if err != nil {
		log.Fatal(err)
	}
	defer os.Remove(tempFile.Name())
	defer tempFile.Close()

	if _, err := tempFile.WriteString(content); err != nil {
		log.Fatal(err)
	}
	if _, err := tempFile.Seek(0, 0); err != nil {
		log.Fatal(err)
	}

	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		log.Fatal(err)
	}
	defer listener.Close()

	var serverWG sync.WaitGroup
	serverWG.Add(1)
	go func() {
		defer serverWG.Done()
		conn, err := listener.Accept()
		if err != nil {
			log.Println("accept error:", err)
			return
		}
		defer conn.Close()

		data, err := io.ReadAll(conn)
		if err != nil {
			log.Println("server read error:", err)
			return
		}
		fmt.Printf("server received:\n%s", string(data))
	}()

	conn, err := net.Dial("tcp", listener.Addr().String())
	if err != nil {
		log.Fatal(err)
	}
	tcpConn := conn.(*net.TCPConn)
	defer tcpConn.Close()

	rawConn, err := tcpConn.SyscallConn()
	if err != nil {
		log.Fatal(err)
	}

	var sendErr error
	var offset int64
	fileSize := int64(len(content))
	for offset < fileSize {
		err = rawConn.Write(func(fd uintptr) bool {
			written, writeErr := syscall.Sendfile(int(fd), int(tempFile.Fd()), &offset, int(fileSize-offset))
			if writeErr != nil {
				sendErr = writeErr
				return true
			}
			return written == 0 || offset >= fileSize
		})
		if err != nil {
			log.Fatal(err)
		}
		if sendErr != nil {
			log.Fatal(sendErr)
		}
	}

	serverWG.Wait()
	fmt.Println("linux sendfile demo done")
}
