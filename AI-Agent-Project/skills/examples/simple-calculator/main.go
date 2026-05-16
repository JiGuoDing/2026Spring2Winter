package main

import (
	"encoding/json"
	"fmt"
	"log"
)

func main() {
	handler := NewCalculatorHandler()

	inputs := []SkillInput{
		{Operation: "add", OperandA: 3, OperandB: 5},
		{Operation: "subtract", OperandA: 10, OperandB: 4},
		{Operation: "multiply", OperandA: 7, OperandB: 8},
		{Operation: "divide", OperandA: 20, OperandB: 4},
		{Operation: "divide", OperandA: 10, OperandB: 0},
	}

	for _, input := range inputs {
		inputJSON, _ := json.Marshal(input)
		outputJSON, err := handler.Handle(inputJSON)

		if err != nil {
			log.Printf("❌ %s(%.0f, %.0f) → 错误: %v", input.Operation, input.OperandA, input.OperandB, err)
			continue
		}

		var output SkillOutput
		_ = json.Unmarshal(outputJSON, &output)
		fmt.Printf("✅ %s(%.0f, %.0f) = %.2f\n", input.Operation, input.OperandA, input.OperandB, output.Result)
	}
}
