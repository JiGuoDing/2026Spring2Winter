package main

import (
	"context"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"sync"
	"time"
)

type middleware func(http.Handler) http.Handler

func chain(handler http.Handler, middlewares ...middleware) http.Handler {
	for index := len(middlewares) - 1; index >= 0; index-- {
		handler = middlewares[index](handler)
	}
	return handler
}

func loggerMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		started := time.Now()
		next.ServeHTTP(w, r)
		log.Printf("%s %s took %s", r.Method, r.URL.Path, time.Since(started).Round(time.Millisecond))
	})
}

func authMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("X-Token") != "secret" {
			http.Error(w, "forbidden", http.StatusForbidden)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func recoverMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if recovered := recover(); recovered != nil {
				http.Error(w, fmt.Sprintf("recovered from panic: %v", recovered), http.StatusInternalServerError)
			}
		}()
		next.ServeHTTP(w, r)
	})
}

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("/hello", func(w http.ResponseWriter, r *http.Request) {
		_, _ = io.WriteString(w, "hello http stack")
	})
	mux.HandleFunc("/panic", func(w http.ResponseWriter, r *http.Request) {
		panic("boom")
	})

	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		log.Fatal(err)
	}
	defer listener.Close()

	srv := &http.Server{
		Handler: chain(mux, recoverMiddleware, loggerMiddleware, authMiddleware),
	}

	var serverWG sync.WaitGroup
	serverWG.Add(1)
	go func() {
		defer serverWG.Done()
		if err := srv.Serve(listener); err != nil && err != http.ErrServerClosed {
			log.Println("http server error:", err)
		}
	}()

	client := &http.Client{
		Timeout: 2 * time.Second,
		Transport: &http.Transport{
			MaxIdleConns:        10,
			MaxIdleConnsPerHost: 4,
			IdleConnTimeout:     30 * time.Second,
		},
	}

	baseURL := "http://" + listener.Addr().String()
	req, err := http.NewRequest(http.MethodGet, baseURL+"/hello", nil)
	if err != nil {
		log.Fatal(err)
	}
	req.Header.Set("X-Token", "secret")
	resp, err := client.Do(req)
	if err != nil {
		log.Fatal(err)
	}
	body, _ := io.ReadAll(resp.Body)
	resp.Body.Close()
	fmt.Printf("hello status=%d body=%s\n", resp.StatusCode, string(body))

	panicReq, err := http.NewRequest(http.MethodGet, baseURL+"/panic", nil)
	if err != nil {
		log.Fatal(err)
	}
	panicReq.Header.Set("X-Token", "secret")
	panicResp, err := client.Do(panicReq)
	if err != nil {
		log.Fatal(err)
	}
	panicBody, _ := io.ReadAll(panicResp.Body)
	panicResp.Body.Close()
	fmt.Printf("panic status=%d body=%s\n", panicResp.StatusCode, string(panicBody))

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctx); err != nil {
		log.Fatal(err)
	}
	serverWG.Wait()
}
