package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"net/http"
	"time"
)

type SearchConfig struct {
	Timeout     time.Duration
	MaxRetries  int
	RetryDelay  time.Duration
	APIKey      string
}

type SearchResult struct {
	Title   string `json:"title"`
	URL     string `json:"url"`
	Snippet string `json:"snippet"`
}

type SearchResponse struct {
	Results []SearchResult `json:"results"`
	Total   int            `json:"total"`
	Cached  bool           `json:"cached"`
}

type SearchClient struct {
	config     SearchConfig
	httpClient *http.Client
	cache      *MemoryCache
}

func NewSearchClient(config SearchConfig, cache *MemoryCache) *SearchClient {
	return &SearchClient{
		config: config,
		httpClient: &http.Client{
			Timeout: config.Timeout,
		},
		cache: cache,
	}
}

func (c *SearchClient) Search(ctx context.Context, query, engine string, maxResults int) (*SearchResponse, error) {
	cacheKey := fmt.Sprintf("%s:%s:%d", engine, query, maxResults)
	if cached, ok := c.cache.Get(cacheKey); ok {
		resp := cached.(*SearchResponse)
		resp.Cached = true
		return resp, nil
	}

	var resp *SearchResponse
	var err error

	for attempt := 0; attempt <= c.config.MaxRetries; attempt++ {
		if attempt > 0 {
			delay := c.config.RetryDelay * time.Duration(math.Pow(2, float64(attempt-1)))
			select {
			case <-ctx.Done():
				return nil, ctx.Err()
			case <-time.After(delay):
			}
		}

		resp, err = c.doSearch(ctx, query, engine, maxResults)
		if err == nil {
			c.cache.Set(cacheKey, resp)
			return resp, nil
		}
	}

	return nil, fmt.Errorf("搜索失败(重试%d次): %w", c.config.MaxRetries, err)
}

func (c *SearchClient) doSearch(ctx context.Context, query, engine string, maxResults int) (*SearchResponse, error) {
	url := c.buildURL(query, engine, maxResults)

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return nil, fmt.Errorf("创建请求失败: %w", err)
	}

	if c.config.APIKey != "" {
		req.Header.Set("Authorization", "Bearer "+c.config.APIKey)
	}

	httpResp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("请求失败: %w", err)
	}
	defer httpResp.Body.Close()

	if httpResp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(httpResp.Body)
		return nil, fmt.Errorf("API返回错误: status=%d, body=%s", httpResp.StatusCode, string(body))
	}

	var resp SearchResponse
	if err := json.NewDecoder(httpResp.Body).Decode(&resp); err != nil {
		return nil, fmt.Errorf("解析响应失败: %w", err)
	}

	return &resp, nil
}

func (c *SearchClient) buildURL(query, engine string, maxResults int) string {
	switch engine {
	case "google":
		return fmt.Sprintf("https://www.googleapis.com/customsearch/v1?q=%s&num=%d", query, maxResults)
	case "bing":
		return fmt.Sprintf("https://api.bing.microsoft.com/v7.0/search?q=%s&count=%d", query, maxResults)
	case "duckduckgo":
		return fmt.Sprintf("https://api.duckduckgo.com/?q=%s&format=json", query)
	default:
		return fmt.Sprintf("https://api.example.com/search?q=%s&limit=%d", query, maxResults)
	}
}
