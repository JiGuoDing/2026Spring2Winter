package main

import (
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

type GeneratorInput struct {
	TemplateName string      `json:"template_name"`
	Language     string      `json:"language"`
	Variables    TemplateVars `json:"variables,omitempty"`
	Validate     bool        `json:"validate,omitempty"`
}

type GeneratorOutput struct {
	Code     string   `json:"code"`
	Language string   `json:"language"`
	Valid    bool     `json:"valid"`
	Errors   []string `json:"errors,omitempty"`
}

type CodeGeneratorHandler struct {
	templates *TemplateManager
	validator *CodeValidator
}

func NewCodeGeneratorHandler(templates *TemplateManager, validator *CodeValidator) *CodeGeneratorHandler {
	return &CodeGeneratorHandler{
		templates: templates,
		validator: validator,
	}
}

func (h *CodeGeneratorHandler) ValidateInput(input json.RawMessage) error {
	var in GeneratorInput
	if err := json.Unmarshal(input, &in); err != nil {
		return &SkillError{
			Code:    "INVALID_INPUT",
			Message: "无法解析输入参数",
			Detail:  err.Error(),
		}
	}

	if in.TemplateName == "" {
		return &SkillError{
			Code:    "MISSING_TEMPLATE",
			Message: "模板名称不能为空",
		}
	}

	validLangs := map[string]bool{"go": true, "python": true, "typescript": true}
	if !validLangs[in.Language] {
		return &SkillError{
			Code:    "INVALID_LANGUAGE",
			Message: "不支持的目标语言",
			Detail:  fmt.Sprintf("language=%s, 支持: go, python, typescript", in.Language),
		}
	}

	if _, exists := h.templates.Get(in.TemplateName, in.Language); !exists {
		return &SkillError{
			Code:    "TEMPLATE_NOT_FOUND",
			Message: "模板不存在",
			Detail:  fmt.Sprintf("template=%s, language=%s", in.TemplateName, in.Language),
		}
	}

	return nil
}

func (h *CodeGeneratorHandler) Handle(input json.RawMessage) (json.RawMessage, error) {
	if err := h.ValidateInput(input); err != nil {
		return nil, err
	}

	var in GeneratorInput
	_ = json.Unmarshal(input, &in)

	code, err := h.templates.Execute(in.TemplateName, in.Language, in.Variables)
	if err != nil {
		return nil, &SkillError{
			Code:    "TEMPLATE_ERROR",
			Message: "模板执行失败",
			Detail:  err.Error(),
		}
	}

	output := GeneratorOutput{
		Code:     code,
		Language: in.Language,
		Valid:    true,
	}

	if in.Validate {
		validationErrors, valid := h.validator.Validate(code, in.Language)
		output.Valid = valid
		if !valid {
			errStrs := make([]string, 0, len(validationErrors))
			for _, ve := range validationErrors {
				errStrs = append(errStrs, fmt.Sprintf("Line %d: %s", ve.Line, ve.Message))
			}
			output.Errors = errStrs
		}
	}

	return json.Marshal(output)
}
