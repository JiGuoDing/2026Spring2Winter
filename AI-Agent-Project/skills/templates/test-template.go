package main

import (
	"encoding/json"
	"errors"
	"testing"
)

func Test{{HANDLER_NAME}}Handler_Validate(t *testing.T) {
	handler := New{{HANDLER_NAME}}Handler()

	tests := []struct {
		name    string
		input   string
		wantErr bool
		errCode string
	}{
		{
			name:    "有效输入",
			input:   `{}`,
			wantErr: false,
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

func Test{{HANDLER_NAME}}Handler_Handle(t *testing.T) {
	handler := New{{HANDLER_NAME}}Handler()

	input, _ := json.Marshal(SkillInput{})
	outputJSON, err := handler.Handle(input)
	if err != nil {
		t.Fatalf("Handle() error = %v", err)
	}

	var output SkillOutput
	if err := json.Unmarshal(outputJSON, &output); err != nil {
		t.Fatalf("解析输出失败: %v", err)
	}
}

func Benchmark{{HANDLER_NAME}}Handler_Handle(b *testing.B) {
	handler := New{{HANDLER_NAME}}Handler()
	input, _ := json.Marshal(SkillInput{})

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = handler.Handle(input)
	}
}
