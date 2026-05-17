//go:build !linux

package main

import "fmt"

func main() {
	fmt.Println("sendfile demo only runs on Linux; see the README for the platform note.")
}
