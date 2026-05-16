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
	Operation string  `json:"operation"`
	OperandA  float64 `json:"operand_a"`
	OperandB  float64 `json:"operand_b"`
}

type SkillOutput struct {
	Result    float64 `json:"result"`
	Operation string  `json:"operation"`
}

type CalculatorHandler struct{}

func NewCalculatorHandler() *CalculatorHandler {
	return &CalculatorHandler{}
}

func (h *CalculatorHandler) Validate(input json.RawMessage) error {
	var in SkillInput
	if err := json.Unmarshal(input, &in); err != nil {
		return &SkillError{
			Code:    "INVALID_INPUT",
			Message: "无法解析输入参数",
			Detail:  err.Error(),
		}
	}

	validOps := map[string]bool{
		"add": true, "subtract": true,
		"multiply": true, "divide": true,
	}
	if !validOps[in.Operation] {
		return &SkillError{
			Code:    "INVALID_OPERATION",
			Message: "不支持的运算类型",
			Detail:  fmt.Sprintf("operation=%s, 支持的类型: add, subtract, multiply, divide", in.Operation),
		}
	}

	return nil
}

func (h *CalculatorHandler) Handle(input json.RawMessage) (json.RawMessage, error) {
	if err := h.Validate(input); err != nil {
		return nil, err
	}

	var in SkillInput
	_ = json.Unmarshal(input, &in)

	var result float64
	switch in.Operation {
	case "add":
		result = in.OperandA + in.OperandB
	case "subtract":
		result = in.OperandA - in.OperandB
	case "multiply":
		result = in.OperandA * in.OperandB
	case "divide":
		if in.OperandB == 0 {
			return nil, &SkillError{
				Code:    "DIVISION_BY_ZERO",
				Message: "除数不能为零",
				Detail:  fmt.Sprintf("operand_a=%.2f, operand_b=0", in.OperandA),
			}
		}
		result = in.OperandA / in.OperandB
	}

	output := SkillOutput{
		Result:    result,
		Operation: in.Operation,
	}

	return json.Marshal(output)
}
