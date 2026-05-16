package main

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func newTestServer(statusCode int, body string) *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(statusCode)
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(body))
	}))
}

func TestWebSearchHandler_Validate(t *testing.T) {
	cache := NewMemoryCache(5 * time.Minute)
	client := NewSearchClient(SearchConfig{Timeout: 5 * time.Second}, cache)
	handler := NewWebSearchHandler(client)

	tests := []struct {
		name    string
		input   string
		wantErr bool
		errCode string
	}{
		{
			name:    "有效输入",
			input:   `{"query":"golang tutorial"}`,
			wantErr: false,
		},
		{
			name:    "空查询",
			input:   `{"query":""}`,
			wantErr: true,
			errCode: "MISSING_QUERY",
		},
		{
			name:    "无效引擎",
			input:   `{"query":"test","engine":"baidu"}`,
			wantErr: true,
			errCode: "INVALID_ENGINE",
		},
		{
			name:    "无效JSON",
			input:   `{invalid}`,
			wantErr: true,
			errCode: "INVALID_INPUT",
		},
		{
			name:    "结果数量超限",
			input:   `{"query":"test","max_results":200}`,
			wantErr: true,
			errCode: "INVALID_MAX_RESULTS",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := handler.Validate(json.RawMessage(tt.input))
			if tt.wantErr {
				if err == nil {
					t.Fatal("期望错误，但未返回")
				}
				var skillErr *SkillError
				if errors.As(err, &skillErr) && skillErr.Code != tt.errCode {
					t.Errorf("错误码 = %s, 期望 %s", skillErr.Code, tt.errCode)
				}
				return
			}
			if err != nil {
				t.Errorf("未期望错误: %v", err)
			}
		})
	}
}

func TestWebSearchHandler_Handle_Success(t *testing.T) {
	mockResp := `{
		"results": [
			{"title": "Go Tutorial", "url": "https://go.dev/tour", "snippet": "Welcome to the Go tutorial"},
			{"title": "Go by Example", "url": "https://gobyexample.com", "snippet": "Go examples"}
		],
		"total": 2
	}`

	server := newTestServer(http.StatusOK, mockResp)
	defer server.Close()

	cache := NewMemoryCache(5 * time.Minute)
	client := NewSearchClient(SearchConfig{
		Timeout:    5 * time.Second,
		MaxRetries: 2,
	}, cache)

	handler := NewWebSearchHandler(client)

	input, _ := json.Marshal(SearchInput{Query: "golang", Engine: "google", MaxResults: 5})
	outputJSON, err := handler.Handle(context.Background(), input)
	if err != nil {
		t.Fatalf("Handle() error = %v", err)
	}

	var output SearchOutput
	if err := json.Unmarshal(outputJSON, &output); err != nil {
		t.Fatalf("解析输出失败: %v", err)
	}

	if output.Total != 2 {
		t.Errorf("总结果数 = %d, 期望 2", output.Total)
	}
	if len(output.Results) != 2 {
		t.Errorf("结果数 = %d, 期望 2", len(output.Results))
	}
}

func TestWebSearchHandler_Handle_Cache(t *testing.T) {
	callCount := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		callCount++
		w.WriteHeader(http.StatusOK)
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"results":[{"title":"test","url":"https://example.com","snippet":"test"}],"total":1}`))
	}))
	defer server.Close()

	cache := NewMemoryCache(5 * time.Minute)
	client := NewSearchClient(SearchConfig{Timeout: 5 * time.Second}, cache)
	handler := NewWebSearchHandler(client)

	input, _ := json.Marshal(SearchInput{Query: "cache-test", Engine: "google"})

	_, _ = handler.Handle(context.Background(), input)
	_, _ = handler.Handle(context.Background(), input)

	if callCount != 1 {
		t.Errorf("API调用次数 = %d, 期望 1 (第二次应命中缓存)", callCount)
	}
}

func TestMemoryCache(t *testing.T) {
	cache := NewMemoryCache(100 * time.Millisecond)

	cache.Set("key1", "value1")

	val, ok := cache.Get("key1")
	if !ok || val != "value1" {
		t.Error("缓存读取失败")
	}

	_, ok = cache.Get("nonexistent")
	if ok {
		t.Error("不存在的键应返回 false")
	}

	time.Sleep(150 * time.Millisecond)
	_, ok = cache.Get("key1")
	if ok {
		t.Error("过期键应返回 false")
	}
}
