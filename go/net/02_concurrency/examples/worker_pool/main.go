package main

import (
	"bufio"
	"context"
	"fmt"
	"io"
	"log"
	"net"
	"sync"
	"time"
)

type Task struct {
	ID   int
	Text string
	Run  func(context.Context) error
}

type Result struct {
	ID      int
	Elapsed time.Duration
	Err     error
}

type Pool struct {
	jobs    chan Task
	results chan Result
	ctx     context.Context
	cancel  context.CancelFunc
	wg      sync.WaitGroup
}

func NewPool(workerCount, queueSize int) *Pool {
	ctx, cancel := context.WithCancel(context.Background())
	pool := &Pool{
		jobs:    make(chan Task, queueSize),
		results: make(chan Result, queueSize),
		ctx:     ctx,
		cancel:  cancel,
	}
	for i := 0; i < workerCount; i++ {
		pool.wg.Add(1)
		go func(workerID int) {
			defer pool.wg.Done()
			for task := range pool.jobs {
				started := time.Now()
				err := task.Run(pool.ctx)
				pool.results <- Result{ID: task.ID, Elapsed: time.Since(started), Err: err}
			}
		}(i + 1)
	}
	go func() {
		pool.wg.Wait()
		close(pool.results)
	}()
	return pool
}

func (p *Pool) Submit(task Task) error {
	select {
	case p.jobs <- task:
		return nil
	case <-p.ctx.Done():
		return p.ctx.Err()
	}
}

func (p *Pool) Close() {
	close(p.jobs)
}

func (p *Pool) Stop() {
	p.cancel()
}

func (p *Pool) Results() <-chan Result {
	return p.results
}

func startEchoServer() (string, func()) {
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
				r := bufio.NewReader(c)
				line, err := r.ReadString('\n')
				if err != nil {
					return
				}
				_, _ = io.WriteString(c, "echo: "+line)
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

func runClientTask(ctx context.Context, addr, text string) error {
	dialer := net.Dialer{Timeout: 2 * time.Second}
	conn, err := dialer.DialContext(ctx, "tcp", addr)
	if err != nil {
		return err
	}
	defer conn.Close()

	if err := conn.SetDeadline(time.Now().Add(2 * time.Second)); err != nil {
		return err
	}
	if _, err := fmt.Fprintf(conn, "%s\n", text); err != nil {
		return err
	}
	reply, err := bufio.NewReader(conn).ReadString('\n')
	if err != nil {
		return err
	}
	fmt.Printf("task %q -> %s", text, reply)
	return nil
}

func main() {
	addr, stopServer := startEchoServer()
	defer stopServer()

	pool := NewPool(2, 4)
	messages := []string{"alpha", "beta", "gamma", "delta", "epsilon"}

	go func() {
		for index, message := range messages {
			message := message
			_ = pool.Submit(Task{
				ID:   index + 1,
				Text: message,
				Run: func(ctx context.Context) error {
					return runClientTask(ctx, addr, message)
				},
			})
		}
		pool.Close()
	}()

	for result := range pool.Results() {
		fmt.Printf("result #%d took %s, err=%v\n", result.ID, result.Elapsed.Round(time.Millisecond), result.Err)
	}
}
