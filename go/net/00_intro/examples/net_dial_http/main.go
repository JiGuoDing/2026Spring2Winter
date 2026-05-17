package main

import (
	"bufio"
	"fmt"
	"io"
	"log"
	"net"
	"strings"
	"sync"
)

func main() {
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

		r := bufio.NewReader(conn)
		for {
			line, err := r.ReadString('\n')
			if err != nil {
				log.Println("read request error:", err)
				return
			}
			if strings.TrimSpace(line) == "" {
				break
			}
		}

		body := "hello from manual http server"
		response := fmt.Sprintf(
			"HTTP/1.1 200 OK\r\nContent-Length: %d\r\nContent-Type: text/plain; charset=utf-8\r\nConnection: close\r\n\r\n%s",
			len(body), body,
		)
		if _, err := io.WriteString(conn, response); err != nil {
			log.Println("write response error:", err)
		}
	}()

	conn, err := net.Dial("tcp", listener.Addr().String())
	if err != nil {
		log.Fatal(err)
	}
	defer conn.Close()

	request := fmt.Sprintf("GET /hello HTTP/1.1\r\nHost: %s\r\nConnection: close\r\n\r\n", listener.Addr().String())
	if _, err := io.WriteString(conn, request); err != nil {
		log.Fatal(err)
	}

	response, err := io.ReadAll(conn)
	if err != nil {
		log.Fatal(err)
	}

	fmt.Println("client received:")
	fmt.Println(string(response))

	serverWG.Wait()
}
