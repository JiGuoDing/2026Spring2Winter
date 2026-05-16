package main

import (
	"encoding/json"
	"fmt"
)

func main() {
	router := NewIntentRouter(0.3)
	RegisterDefaultRoutes(router)
	ctx := NewContextManager(10)
	handler := NewMultiModalHandler(router, ctx)

	inputs := []AssistantInput{
		{Message: "你好，我想了解一些东西", SessionID: "demo-session", Modality: "text"},
		{Message: "什么是AI Agent技能？", SessionID: "demo-session", Modality: "text"},
		{Message: "这段代码有bug，帮我看看", SessionID: "demo-session", Modality: "text"},
		{Message: "帮我分析这张图片", SessionID: "demo-session", Modality: "image", ImageURL: "https://example.com/photo.jpg"},
		{Message: "今天天气真好", SessionID: "demo-session", Modality: "text"},
	}

	for _, input := range inputs {
		inputJSON, _ := json.Marshal(input)
		outputJSON, err := handler.Handle(inputJSON)

		if err != nil {
			fmt.Printf("❌ 处理失败: %v\n", err)
			continue
		}

		var output AssistantOutput
		_ = json.Unmarshal(outputJSON, &output)

		fmt.Printf("✅ [%s] %.0f%% → %s\n", output.Intent, output.Confidence*100, output.Response)
		if len(output.SubSkills) > 0 {
			fmt.Printf("   子技能: %v\n", output.SubSkills)
		}
	}

	fmt.Printf("\n📊 会话历史 (%d条消息):\n", len(ctx.GetHistory("demo-session")))
	for _, msg := range ctx.GetHistory("demo-session") {
		fmt.Printf("   [%s] %s\n", msg.Role, msg.Content)
	}
}
