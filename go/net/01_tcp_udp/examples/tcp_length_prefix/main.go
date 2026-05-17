package main

import (
	"encoding/binary"
	"fmt"
	"io"
	"log"
	"net"
	"sync"
	"time"
)

func writeFrame(conn *net.TCPConn, payload []byte) error {
	var header [4]byte
	binary.BigEndian.PutUint32(header[:], uint32(len(payload)))
	if _, err := conn.Write(header[:]); err != nil {
		return err
	}
	_, err := conn.Write(payload)
	return err
}

func readFrame(conn *net.TCPConn) ([]byte, error) {
	var header [4]byte
	if _, err := io.ReadFull(conn, header[:]); err != nil {
		return nil, err
	}
	length := binary.BigEndian.Uint32(header[:])
	payload := make([]byte, length)
	_, err := io.ReadFull(conn, payload)
	return payload, err
}

func main() {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		log.Fatal(err)
	}
	defer listener.Close()

	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		defer wg.Done()
		conn, err := listener.Accept()
		if err != nil {
			log.Println("accept error:", err)
			return
		}
		tcpConn := conn.(*net.TCPConn)
		defer tcpConn.Close()
		_ = tcpConn.SetDeadline(time.Now().Add(3 * time.Second))

		message, err := readFrame(tcpConn)
		if err != nil {
			log.Println("server read error:", err)
			return
		}
		fmt.Println("server recv:", string(message))

		if err := writeFrame(tcpConn, []byte("echo: "+string(message))); err != nil {
			log.Println("server write error:", err)
			return
		}
		_ = tcpConn.CloseWrite()
	}()

	tcpAddr, err := net.ResolveTCPAddr("tcp", listener.Addr().String())
	if err != nil {
		log.Fatal(err)
	}
	client, err := net.DialTCP("tcp", nil, tcpAddr)
	if err != nil {
		log.Fatal(err)
	}
	defer client.Close()
	_ = client.SetDeadline(time.Now().Add(3 * time.Second))

	if err := writeFrame(client, []byte("hello length prefix")); err != nil {
		log.Fatal(err)
	}
	reply, err := readFrame(client)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println("client recv:", string(reply))
	_ = client.CloseWrite()
	_ = client.CloseRead()

	wg.Wait()
}
