package main

import (
	"fmt"
	"log"
	"net"
	"sync"
	"time"
)

func main() {
	serverAddr, err := net.ResolveUDPAddr("udp", "127.0.0.1:0")
	if err != nil {
		log.Fatal(err)
	}
	serverConn, err := net.ListenUDP("udp", serverAddr)
	if err != nil {
		log.Fatal(err)
	}
	defer serverConn.Close()

	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		defer wg.Done()
		buffer := make([]byte, 1024)
		_ = serverConn.SetReadDeadline(time.Now().Add(3 * time.Second))
		n, remote, err := serverConn.ReadFromUDP(buffer)
		if err != nil {
			log.Println("udp server read error:", err)
			return
		}
		message := string(buffer[:n])
		fmt.Println("server recv:", message)
		reply := []byte("echo: " + message)
		if _, err := serverConn.WriteToUDP(reply, remote); err != nil {
			log.Println("udp server write error:", err)
		}
	}()

	clientAddr, err := net.ResolveUDPAddr("udp", "127.0.0.1:0")
	if err != nil {
		log.Fatal(err)
	}
	conn, err := net.DialUDP("udp", clientAddr, serverConn.LocalAddr().(*net.UDPAddr))
	if err != nil {
		log.Fatal(err)
	}
	defer conn.Close()

	_ = conn.SetDeadline(time.Now().Add(3 * time.Second))
	if _, err := conn.Write([]byte("hello udp")); err != nil {
		log.Fatal(err)
	}
	buffer := make([]byte, 1024)
	n, err := conn.Read(buffer)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println("client recv:", string(buffer[:n]))

	wg.Wait()
}
