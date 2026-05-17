package main

import (
	"encoding/json"
	"testing"
)

func TestHelloWorldHandler(t *testing.T) {
	input, _ := json.Marshal(HelloWorldInput{Name: "Developer"})
	output, err := HelloWorldHandler(input)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	var out HelloWorldOutput
	json.Unmarshal(output, &out)

	if out.Greeting == "" {
		t.Error("greeting should not be empty")
	}
}

func TestHelloWorldHandler_EmptyName(t *testing.T) {
	input, _ := json.Marshal(HelloWorldInput{Name: ""})
	_, err := HelloWorldHandler(input)
	if err == nil {
		t.Fatal("expected error for empty name")
	}
}
