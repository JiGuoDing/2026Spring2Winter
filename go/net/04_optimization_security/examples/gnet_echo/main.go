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

type message struct {
	conn net.Conn
	text string
}

type reactorServer struct {
	ready       chan struct{}
	done        chan struct{}
	once        sync.Once
	events      chan message
	connections map[net.Conn]struct{}
	mu          sync.Mutex
}

func newReactorServer() *reactorServer {
	return &reactorServer{
		ready:       make(chan struct{}),
		done:        make(chan struct{}),
		events:      make(chan message, 16),
		connections: make(map[net.Conn]struct{}),
	}
}

func (s *reactorServer) signalDone() {
	s.once.Do(func() {
		close(s.done)
	})
}

func (s *reactorServer) add(conn net.Conn) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.connections[conn] = struct{}{}
}

func (s *reactorServer) remove(conn net.Conn) {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.connections, conn)
}

func (s *reactorServer) run(listener net.Listener) {
	close(s.ready)

	go s.eventLoop()

	for {
		conn, err := listener.Accept()
		if err != nil {
			select {
			case <-s.done:
				return
			default:
				log.Println("accept error:", err)
				return
			}
		}
		s.add(conn)
		go s.handleConn(conn)
	}
}

func (s *reactorServer) handleConn(conn net.Conn) {
	defer func() {
		s.remove(conn)
		_ = conn.Close()
	}()

	_, _ = io.WriteString(conn, "welcome reactor\n")
	reader := bufio.NewReader(conn)
	for {
		line, err := reader.ReadString('\n')
		if err != nil {
			return
		}
		select {
		case s.events <- message{conn: conn, text: line}:
		case <-s.done:
			return
		}
	}
}

func (s *reactorServer) eventLoop() {
	for {
		select {
		case msg := <-s.events:
			_, _ = fmt.Fprintf(msg.conn, "echo: %s", msg.text)
			if strings.TrimSpace(msg.text) == "quit" {
				s.signalDone()
				return
			}
		case <-s.done:
			return
		}
	}
}

func main() {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		log.Fatal(err)
	}
	defer listener.Close()

	server := newReactorServer()
	var serverWG sync.WaitGroup
	serverWG.Add(1)
	go func() {
		defer serverWG.Done()
		server.run(listener)
	}()

	<-server.ready

	conn, err := net.Dial("tcp", listener.Addr().String())
	if err != nil {
		log.Fatal(err)
	}
	reader := bufio.NewReader(conn)

	welcome, err := reader.ReadString('\n')
	if err != nil {
		log.Fatal(err)
	}
	fmt.Print("client received: ", welcome)

	if _, err := fmt.Fprintln(conn, "hello reactor"); err != nil {
		log.Fatal(err)
	}
	echo, err := reader.ReadString('\n')
	if err != nil {
		log.Fatal(err)
	}
	fmt.Print("client received: ", echo)

	if _, err := fmt.Fprintln(conn, "quit"); err != nil {
		log.Fatal(err)
	}
	quitEcho, err := reader.ReadString('\n')
	if err != nil {
		log.Fatal(err)
	}
	fmt.Print("client received: ", quitEcho)

	<-server.done
	_ = conn.Close()
	serverWG.Wait()
	fmt.Println("reactor server stopped")
}
