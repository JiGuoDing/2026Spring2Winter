package main

import (
	"context"
	"fmt"
	"os"

	"github.com/cloudwego/eino-ext/components/model/ark"
	"github.com/cloudwego/eino/schema"
	"github.com/joho/godotenv"
)

func main() {
	err := godotenv.Load(".env")
	if err != nil {
		panic("Error loading .env file")
	}

	ctx := context.Background()

	model, err := ark.NewChatModel(ctx, &ark.ChatModelConfig{
		APIKey: os.Getenv("ARK_API_KEY"),
		Model:  os.Getenv("MODEL"),
	})

	input := []*schema.Message{
		schema.SystemMessage("你是一个高中生"),
		schema.UserMessage("你好"),
	}

	// * 非流式处理
	// response, err := model.Generate(ctx, input)
	// if err != nil {
	// 	panic("Error generating response")
	// }

	// fmt.Println(response)

	// * 流式处理
	reader, err := model.Stream(ctx, input)
	if err != nil {
		panic("Error streaming response")
	}
	defer reader.Close()

	for {
		chunk, err := reader.Recv()
		if err != nil {
			panic("Error receiving chunk")
		}
		fmt.Print(chunk.Content)
	}

}
