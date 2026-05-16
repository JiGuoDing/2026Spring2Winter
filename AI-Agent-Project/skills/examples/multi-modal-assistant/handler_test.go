package main

import (
	"encoding/json"
	"errors"
	"testing"
)

func setupHandler() *MultiModalHandler {
	router := NewIntentRouter(0.3)
	RegisterDefaultRoutes(router)
	ctx := NewContextManager(10)
	return NewMultiModalHandler(router, ctx)
}

func TestMultiModalHandler_Validate(t *testing.T) {
	handler := setupHandler()

	tests := []struct {
		name    string
		input   string
		wantErr bool
		errCode string
	}{
		{
			name:    "有效文本输入",
			input:   `{"message":"你好","session_id":"s1","modality":"text"}`,
			wantErr: false,
		},
		{
			name:    "空消息",
			input:   `{"message":"","session_id":"s1"}`,
			wantErr: true,
			errCode: "EMPTY_MESSAGE",
		},
		{
			name:    "缺少会话ID",
			input:   `{"message":"hello"}`,
			wantErr: true,
			errCode: "MISSING_SESSION",
		},
		{
			name:    "无效模态",
			input:   `{"message":"test","session_id":"s1","modality":"video"}`,
			wantErr: true,
			errCode: "INVALID_MODALITY",
		},
		{
			name:    "无效JSON",
			input:   `{invalid}`,
			wantErr: true,
			errCode: "INVALID_INPUT",
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

func TestMultiModalHandler_Handle_IntentRouting(t *testing.T) {
	handler := setupHandler()

	tests := []struct {
		name        string
		input       AssistantInput
		wantIntent  string
	}{
		{
			name:        "问候意图",
			input:       AssistantInput{Message: "你好", SessionID: "s1", Modality: "text"},
			wantIntent:  "greeting",
		},
		{
			name:        "问题意图",
			input:       AssistantInput{Message: "什么是AI Agent", SessionID: "s2", Modality: "text"},
			wantIntent:  "question",
		},
		{
			name:        "编程意图",
			input:       AssistantInput{Message: "这段代码有什么问题", SessionID: "s3", Modality: "text"},
			wantIntent:  "code_help",
		},
		{
			name:        "通用意图",
			input:       AssistantInput{Message: "今天天气不错", SessionID: "s4", Modality: "text"},
			wantIntent:  "general",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			inputJSON, _ := json.Marshal(tt.input)
			outputJSON, err := handler.Handle(inputJSON)
			if err != nil {
				t.Fatalf("Handle() error = %v", err)
			}

			var output AssistantOutput
			_ = json.Unmarshal(outputJSON, &output)

			if output.Intent != tt.wantIntent {
				t.Errorf("意图 = %s, 期望 %s", output.Intent, tt.wantIntent)
			}
		})
	}
}

func TestMultiModalHandler_Handle_ContextPersistence(t *testing.T) {
	handler := setupHandler()

	input1, _ := json.Marshal(AssistantInput{Message: "你好", SessionID: "ctx-test", Modality: "text"})
	input2, _ := json.Marshal(AssistantInput{Message: "什么是Go", SessionID: "ctx-test", Modality: "text"})

	_, _ = handler.Handle(input1)
	_, _ = handler.Handle(input2)

	history := handler.context.GetHistory("ctx-test")
	if len(history) != 4 {
		t.Errorf("历史消息数 = %d, 期望 4 (2条用户+2条助手)", len(history))
	}
}

func TestIntentRouter(t *testing.T) {
	router := NewIntentRouter(0.3)
	router.RegisterRoute("test", []string{"测试", "test"}, nil)

	input := &AssistantInput{Message: "这是一个测试消息", Modality: "text"}
	route, err := router.Route(input)
	if err != nil {
		t.Fatalf("Route() error = %v", err)
	}
	if route == nil {
		t.Fatal("期望匹配到路由")
	}
	if route.Intent.Name != "test" {
		t.Errorf("意图 = %s, 期望 test", route.Intent.Name)
	}
}

func TestContextManager(t *testing.T) {
	cm := NewContextManager(2)

	session := cm.GetOrCreateSession("s1")
	if session == nil {
		t.Fatal("会话不应为nil")
	}

	cm.AddMessage("s1", Message{Role: "user", Content: "hello"})
	cm.AddMessage("s1", Message{Role: "assistant", Content: "hi there"})

	history := cm.GetHistory("s1")
	if len(history) != 2 {
		t.Errorf("历史消息数 = %d, 期望 2", len(history))
	}

	cm.AddMessage("s1", Message{Role: "user", Content: "msg3"})
	cm.AddMessage("s1", Message{Role: "assistant", Content: "msg4"})
	cm.AddMessage("s1", Message{Role: "user", Content: "msg5"})
	cm.AddMessage("s1", Message{Role: "assistant", Content: "msg6"})

	history = cm.GetHistory("s1")
	if len(history) > 4 {
		t.Errorf("maxTurns=2, 历史消息数应不超过4, 实际 %d", len(history))
	}
}
