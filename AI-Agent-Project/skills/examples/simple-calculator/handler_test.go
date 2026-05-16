package main

import (
	"encoding/json"
	"testing"
)

func TestCalculatorHandler_Handle(t *testing.T) {
	handler := NewCalculatorHandler()

	tests := []struct {
		name        string
		input       SkillInput
		wantResult  float64
		wantErrCode string
	}{
		{
			name:        "加法",
			input:       SkillInput{Operation: "add", OperandA: 3, OperandB: 5},
			wantResult:  8,
			wantErrCode: "",
		},
		{
			name:        "减法",
			input:       SkillInput{Operation: "subtract", OperandA: 10, OperandB: 4},
			wantResult:  6,
			wantErrCode: "",
		},
		{
			name:        "乘法",
			input:       SkillInput{Operation: "multiply", OperandA: 7, OperandB: 8},
			wantResult:  56,
			wantErrCode: "",
		},
		{
			name:        "除法",
			input:       SkillInput{Operation: "divide", OperandA: 20, OperandB: 4},
			wantResult:  5,
			wantErrCode: "",
		},
		{
			name:        "除零错误",
			input:       SkillInput{Operation: "divide", OperandA: 10, OperandB: 0},
			wantResult:  0,
			wantErrCode: "DIVISION_BY_ZERO",
		},
		{
			name:        "无效运算类型",
			input:       SkillInput{Operation: "modulo", OperandA: 10, OperandB: 3},
			wantResult:  0,
			wantErrCode: "INVALID_OPERATION",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			inputJSON, _ := json.Marshal(tt.input)
			outputJSON, err := handler.Handle(inputJSON)

			if tt.wantErrCode != "" {
				if err == nil {
					t.Fatalf("期望错误码 %s，但未返回错误", tt.wantErrCode)
				}
				skillErr, ok := err.(*SkillError)
				if !ok {
					t.Fatalf("期望 SkillError 类型，实际: %T", err)
				}
				if skillErr.Code != tt.wantErrCode {
					t.Errorf("错误码 = %s, 期望 %s", skillErr.Code, tt.wantErrCode)
				}
				return
			}

			if err != nil {
				t.Fatalf("未期望错误: %v", err)
			}

			var output SkillOutput
			if err := json.Unmarshal(outputJSON, &output); err != nil {
				t.Fatalf("解析输出失败: %v", err)
			}

			if output.Result != tt.wantResult {
				t.Errorf("结果 = %f, 期望 %f", output.Result, tt.wantResult)
			}

			if output.Operation != tt.input.Operation {
				t.Errorf("运算类型 = %s, 期望 %s", output.Operation, tt.input.Operation)
			}
		})
	}
}

func TestCalculatorHandler_Validate(t *testing.T) {
	handler := NewCalculatorHandler()

	tests := []struct {
		name    string
		input   string
		wantErr bool
	}{
		{
			name:    "有效输入",
			input:   `{"operation":"add","operand_a":1,"operand_b":2}`,
			wantErr: false,
		},
		{
			name:    "无效JSON",
			input:   `{invalid}`,
			wantErr: true,
		},
		{
			name:    "缺少必填字段",
			input:   `{"operation":"add"}`,
			wantErr: false,
		},
		{
			name:    "无效运算类型",
			input:   `{"operation":"power","operand_a":2,"operand_b":3}`,
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := handler.Validate(json.RawMessage(tt.input))
			if (err != nil) != tt.wantErr {
				t.Errorf("Validate() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

func BenchmarkCalculatorHandler_Handle(b *testing.B) {
	handler := NewCalculatorHandler()
	input, _ := json.Marshal(SkillInput{Operation: "add", OperandA: 3, OperandB: 5})

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = handler.Handle(input)
	}
}
