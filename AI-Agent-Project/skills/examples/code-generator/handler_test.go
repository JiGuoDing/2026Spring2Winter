package main

import (
	"encoding/json"
	"errors"
	"testing"
)

func setupGenerator() *CodeGeneratorHandler {
	templates := NewTemplateManager()
	validator := NewCodeValidator()
	return NewCodeGeneratorHandler(templates, validator)
}

func TestCodeGeneratorHandler_ValidateInput(t *testing.T) {
	handler := setupGenerator()

	tests := []struct {
		name    string
		input   string
		wantErr bool
		errCode string
	}{
		{
			name:    "有效输入",
			input:   `{"template_name":"handler","language":"go"}`,
			wantErr: false,
		},
		{
			name:    "缺少模板名",
			input:   `{"template_name":"","language":"go"}`,
			wantErr: true,
			errCode: "MISSING_TEMPLATE",
		},
		{
			name:    "无效语言",
			input:   `{"template_name":"handler","language":"rust"}`,
			wantErr: true,
			errCode: "INVALID_LANGUAGE",
		},
		{
			name:    "模板不存在",
			input:   `{"template_name":"nonexistent","language":"go"}`,
			wantErr: true,
			errCode: "TEMPLATE_NOT_FOUND",
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
			err := handler.ValidateInput(json.RawMessage(tt.input))
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

func TestCodeGeneratorHandler_Handle_GoHandler(t *testing.T) {
	handler := setupGenerator()

	input, _ := json.Marshal(GeneratorInput{
		TemplateName: "handler",
		Language:     "go",
		Variables: TemplateVars{
			"Package":     "main",
			"HandlerName": "User",
		},
		Validate: true,
	})

	outputJSON, err := handler.Handle(input)
	if err != nil {
		t.Fatalf("Handle() error = %v", err)
	}

	var output GeneratorOutput
	_ = json.Unmarshal(outputJSON, &output)

	if output.Language != "go" {
		t.Errorf("语言 = %s, 期望 go", output.Language)
	}
	if output.Code == "" {
		t.Error("生成的代码不应为空")
	}
	if !output.Valid {
		t.Errorf("Go代码应通过校验, errors: %v", output.Errors)
	}
}

func TestCodeGeneratorHandler_Handle_PythonHandler(t *testing.T) {
	handler := setupGenerator()

	input, _ := json.Marshal(GeneratorInput{
		TemplateName: "handler",
		Language:     "python",
		Variables: TemplateVars{
			"HandlerName": "User",
		},
		Validate: true,
	})

	outputJSON, err := handler.Handle(input)
	if err != nil {
		t.Fatalf("Handle() error = %v", err)
	}

	var output GeneratorOutput
	_ = json.Unmarshal(outputJSON, &output)

	if output.Language != "python" {
		t.Errorf("语言 = %s, 期望 python", output.Language)
	}
}

func TestCodeGeneratorHandler_Handle_TypeScriptHandler(t *testing.T) {
	handler := setupGenerator()

	input, _ := json.Marshal(GeneratorInput{
		TemplateName: "handler",
		Language:     "typescript",
		Variables: TemplateVars{
			"HandlerName": "User",
		},
		Validate: true,
	})

	outputJSON, err := handler.Handle(input)
	if err != nil {
		t.Fatalf("Handle() error = %v", err)
	}

	var output GeneratorOutput
	_ = json.Unmarshal(outputJSON, &output)

	if output.Language != "typescript" {
		t.Errorf("语言 = %s, 期望 typescript", output.Language)
	}
}

func TestCodeValidator(t *testing.T) {
	validator := NewCodeValidator()

	_, valid := validator.Validate("package main\nfunc hello() {}", "go")
	if !valid {
		t.Error("有效Go代码应通过校验")
	}

	_, valid = validator.Validate("no package here", "go")
	if valid {
		t.Error("缺少package声明的Go代码应校验失败")
	}

	_, valid = validator.Validate("class User:\n    pass", "python")
	if !valid {
		t.Error("有效Python代码应通过校验")
	}

	_, valid = validator.Validate("class Handler {\n  constructor() {}\n}", "typescript")
	if !valid {
		t.Error("有效TypeScript代码应通过校验")
	}
}

func TestTemplateManager_ListTemplates(t *testing.T) {
	tm := NewTemplateManager()
	templates := tm.ListTemplates()

	if len(templates) == 0 {
		t.Error("应存在默认模板")
	}
}
