package main

import (
	"fmt"
	"io"
	"log"
	"net"
	"strconv"
	"sync"
	"time"
)

func probe(host string, port int, timeout time.Duration) string {
	address := net.JoinHostPort(host, strconv.Itoa(port))
	conn, err := net.DialTimeout("tcp", address, timeout)
	if err != nil {
		return fmt.Sprintf("%s closed (%v)", address, err)
	}
	_ = conn.Close()
	return fmt.Sprintf("%s open", address)
}

func startDemoServer() (string, func()) {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		log.Fatal(err)
	}

	var serverWG sync.WaitGroup
	done := make(chan struct{})
	serverWG.Add(1)
	go func() {
		defer serverWG.Done()
		for {
			conn, err := listener.Accept()
			if err != nil {
				select {
				case <-done:
					return
				default:
					log.Println("accept error:", err)
					return
				}
			}
			go func(c net.Conn) {
				defer c.Close()
				_ = c.SetDeadline(time.Now().Add(2 * time.Second))
				_, _ = io.Copy(io.Discard, c)
			}(conn)
		}
	}()

	stop := func() {
		close(done)
		_ = listener.Close()
		serverWG.Wait()
	}
	return listener.Addr().String(), stop
}

func main() {
	serverAddr, stopServer := startDemoServer()
	defer stopServer()

	tcpAddr := mustResolveTCPAddr(serverAddr)
	openPort := tcpAddr.Port
	startPort := openPort - 1
	if startPort < 1 {
		startPort = 1
	}
	endPort := openPort + 1

	const workerCount = 4
	jobs := make(chan int)
	results := make(chan string, endPort-startPort+1)
	var workerWG sync.WaitGroup

	for i := 0; i < workerCount; i++ {
		workerWG.Add(1)
		go func() {
			defer workerWG.Done()
			for port := range jobs {
				results <- probe("127.0.0.1", port, 300*time.Millisecond)
			}
		}()
	}

	go func() {
		for port := startPort; port <= endPort; port++ {
			jobs <- port
		}
		close(jobs)
		workerWG.Wait()
		close(results)
	}()

	fmt.Printf("demo server listens on %s\n", serverAddr)
	for result := range results {
		fmt.Println(result)
	}
}

func mustResolveTCPAddr(address string) *net.TCPAddr {
	resolved, err := net.ResolveTCPAddr("tcp", address)
	if err != nil {
		log.Fatal(err)
	}
	return resolved
}
