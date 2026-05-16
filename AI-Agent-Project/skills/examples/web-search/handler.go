package main

import (
	"context"
	"encoding/json"
	"fmt"
)

type SkillError struct {
	Code    string `json:"code"`
	Message string `json:"message"`
	Detail  string `json:"detail,omitempty"`
}

func (e *SkillError) Error() string {
	return fmt.Sprintf("[%s] %s: %s", e.Code, e.Message, e.Detail)
}

type SearchInput struct {
	Query      string `json:"query"`
	Engine     string `json:"engine,omitempty"`
	MaxResults int    `json:"max_results,omitempty"`
	Language   string `json:"language,omitempty"`
}

type SearchOutput struct {
	Results []SearchResult `json:"results"`
	Total   int            `json:"total"`
	Cached  bool           `json:"cached"`
}

type WebSearchHandler struct {
	client *SearchClient
}

func NewWebSearchHandler(client *SearchClient) *WebSearchHandler {
	return &WebSearchHandler{client: client}
}

func (h *WebSearchHandler) Validate(input json.RawMessage) error {
	var in SearchInput
	if err := json.Unmarshal(input, &in); err != nil {
		return &SkillError{
			Code:    "INVALID_INPUT",
			Message: "无法解析输入参数",
			Detail:  err.Error(),
		}
	}

	if in.Query == "" {
		return &SkillError{
			Code:    "MISSING_QUERY",
			Message: "搜索关键词不能为空",
		}
	}

	validEngines := map[string]bool{
		"google": true, "bing": true, "duckduckgo": true, "": true,
	}
	if !validEngines[in.Engine] {
		return &SkillError{
			Code:    "INVALID_ENGINE",
			Message: "不支持的搜索引擎",
			Detail:  fmt.Sprintf("engine=%s", in.Engine),
		}
	}

	if in.MaxResults < 0 || in.MaxResults > 100 {
		return &SkillError{
			Code:    "INVALID_MAX_RESULTS",
			Message: "结果数量范围: 0-100",
			Detail:  fmt.Sprintf("max_results=%d", in.MaxResults),
		}
	}

	return nil
}

func (h *WebSearchHandler) Handle(ctx context.Context, input json.RawMessage) (json.RawMessage, error) {
	if err := h.Validate(input); err != nil {
		return nil, err
	}

	var in SearchInput
	_ = json.Unmarshal(input, &in)

	if in.Engine == "" {
		in.Engine = "google"
	}
	if in.MaxResults == 0 {
		in.MaxResults = 10
	}

	resp, err := h.client.Search(ctx, in.Query, in.Engine, in.MaxResults)
	if err != nil {
		return nil, &SkillError{
			Code:    "SEARCH_FAILED",
			Message: "搜索请求失败",
			Detail:  err.Error(),
		}
	}

	output := SearchOutput{
		Results: resp.Results,
		Total:   resp.Total,
		Cached:  resp.Cached,
	}

	return json.Marshal(output)
}
