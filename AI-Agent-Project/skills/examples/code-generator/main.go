package main

import (
	"encoding/json"
	"fmt"
)

func main() {
	templates := NewTemplateManager()
	validator := NewCodeValidator()
	handler := NewCodeGeneratorHandler(templates, validator)

	inputs := []GeneratorInput{
		{
			TemplateName: "handler",
			Language:     "go",
			Variables: TemplateVars{
				"Package":     "main",
				"HandlerName": "Calculator",
			},
			Validate: true,
		},
		{
			TemplateName: "handler",
			Language:     "python",
			Variables: TemplateVars{
				"HandlerName": "Calculator",
			},
			Validate: true,
		},
		{
			TemplateName: "handler",
			Language:     "typescript",
			Variables: TemplateVars{
				"HandlerName": "Calculator",
			},
			Validate: true,
		},
		{
			TemplateName: "api",
			Language:     "go",
			Variables: TemplateVars{
				"Package":     "api",
				"HandlerName": "GetUsers",
				"Method":      "GET",
				"Path":        "/users",
			},
			Validate: true,
		},
	}

	for _, input := range inputs {
		inputJSON, _ := json.Marshal(input)
		outputJSON, err := handler.Handle(inputJSON)

		if err != nil {
			fmt.Printf("❌ 生成失败 (%s/%s): %v\n", input.TemplateName, input.Language, err)
			continue
		}

		var output GeneratorOutput
		_ = json.Unmarshal(outputJSON, &output)

		validTag := "✅"
		if !output.Valid {
			validTag = "⚠️"
		}
		fmt.Printf("%s %s/%s (校验: %v)\n", validTag, input.TemplateName, input.Language, output.Valid)
		fmt.Println("---")
		fmt.Println(output.Code)
		fmt.Println("===")
	}
}
