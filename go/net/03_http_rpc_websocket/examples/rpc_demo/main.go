package main

import (
	"errors"
	"fmt"
	"log"
	"net"
	"net/rpc"
	"sync"
)

type Args struct {
	A int
	B int
}

type Reply struct {
	Product int
}

type Calculator struct{}

func (Calculator) Mul(args *Args, reply *Reply) error {
	reply.Product = args.A * args.B
	return nil
}

func main() {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		log.Fatal(err)
	}
	defer listener.Close()

	if err := rpc.RegisterName("Calculator", new(Calculator)); err != nil {
		log.Fatal(err)
	}

	var serverWG sync.WaitGroup
	serverWG.Add(1)
	go func() {
		defer serverWG.Done()
		for {
			conn, err := listener.Accept()
			if err != nil {
				if errors.Is(err, net.ErrClosed) {
					return
				}
				log.Println("rpc accept error:", err)
				return
			}
			go rpc.ServeConn(conn)
		}
	}()

	client, err := rpc.Dial("tcp", listener.Addr().String())
	if err != nil {
		log.Fatal(err)
	}
	defer client.Close()

	var reply Reply
	if err := client.Call("Calculator.Mul", &Args{A: 6, B: 7}, &reply); err != nil {
		log.Fatal(err)
	}
	fmt.Println("rpc reply:", reply.Product)

	_ = listener.Close()
	serverWG.Wait()
}
