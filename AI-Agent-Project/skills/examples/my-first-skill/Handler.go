package main

import (
	"encoding/json"
	"fmt"
)

type HelloWorldInput struct {
	Name string `json:"name"`
}

type HelloWorldOutput struct {
	Greeting string `json:"greeting"`
}

func HelloWorldHandler(input []byte) ([]byte, error) {
	var in HelloWorldInput
	if err := json.Unmarshal(input, &in); err != nil {
		return nil, fmt.Errorf("invalid input: %w", err)
	}

	if in.Name == "" {
		return nil, fmt.Errorf("name is required")
	}

	out := HelloWorldOutput{
		Greeting: fmt.Sprintf("Hello, %s! Welcome to AI Agent Skills.", in.Name),
	}

	return json.Marshal(out)
}
