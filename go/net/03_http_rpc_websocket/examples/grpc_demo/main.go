package main

import "fmt"

func main() {
	fmt.Println("gRPC scaffold")
	fmt.Println("- Contract file: hello.proto")
	fmt.Println("- Service: demo.EchoService")
	fmt.Println("- Request / response type: google.protobuf.StringValue")
	fmt.Println("- Full grpc-go runtime is omitted here because external module fetch is unavailable in this environment.")
	fmt.Println("- When network access is available, replace this scaffold with the generated grpc-go server/client pair.")
}
