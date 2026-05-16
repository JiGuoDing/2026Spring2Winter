package main

import (
	"context"
	"encoding/json"
	"fmt"
	"time"
)

func main() {
	cache := NewMemoryCache(5 * time.Minute)
	client := NewSearchClient(SearchConfig{
		Timeout:    10 * time.Second,
		MaxRetries: 3,
		RetryDelay: 1 * time.Second,
	}, cache)

	handler := NewWebSearchHandler(client)

	inputs := []SearchInput{
		{Query: "golang tutorial", Engine: "google", MaxResults: 5},
		{Query: "rust programming", Engine: "bing", MaxResults: 3},
		{Query: "python web framework", Engine: "duckduckgo"},
	}

	for _, input := range inputs {
		inputJSON, _ := json.Marshal(input)
		outputJSON, err := handler.Handle(context.Background(), inputJSON)

		if err != nil {
			fmt.Printf("❌ 搜索 '%s' 失败: %v\n", input.Query, err)
			continue
		}

		var output SearchOutput
		_ = json.Unmarshal(outputJSON, &output)

		cachedTag := ""
		if output.Cached {
			cachedTag = " (缓存)"
		}
		fmt.Printf("✅ 搜索 '%s'%s → %d 条结果\n", input.Query, cachedTag, output.Total)
		for _, r := range output.Results {
			fmt.Printf("   - %s: %s\n", r.Title, r.URL)
		}
	}
}
