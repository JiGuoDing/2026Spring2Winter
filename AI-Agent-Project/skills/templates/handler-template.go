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

type SkillInput struct {
}

type SkillOutput struct {
}

type {{HANDLER_NAME}}Handler struct{}

func New{{HANDLER_NAME}}Handler() *{{HANDLER_NAME}}Handler {
	return &{{HANDLER_NAME}}Handler{}
}

func (h *{{HANDLER_NAME}}Handler) Validate(input json.RawMessage) error {
	var in SkillInput
	if err := json.Unmarshal(input, &in); err != nil {
		return &SkillError{
			Code:    "INVALID_INPUT",
			Message: "无法解析输入参数",
			Detail:  err.Error(),
		}
	}

	return nil
}

func (h *{{HANDLER_NAME}}Handler) Handle(input json.RawMessage) (json.RawMessage, error) {
	if err := h.Validate(input); err != nil {
		return nil, err
	}

	var in SkillInput
	_ = json.Unmarshal(input, &in)

	output := SkillOutput{}

	return json.Marshal(output)
}
