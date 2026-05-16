package main

import (
	"regexp"
	"strings"
)

type ValidationError struct {
	Line    int    `json:"line"`
	Message string `json:"message"`
}

type CodeValidator struct{}

func NewCodeValidator() *CodeValidator {
	return &CodeValidator{}
}

func (v *CodeValidator) Validate(code, language string) ([]ValidationError, bool) {
	var errors []ValidationError

	switch language {
	case "go":
		errors = v.validateGo(code)
	case "python":
		errors = v.validatePython(code)
	case "typescript":
		errors = v.validateTypeScript(code)
	default:
		errors = append(errors, ValidationError{
			Line:    0,
			Message: "不支持的语言: " + language,
		})
	}

	return errors, len(errors) == 0
}

func (v *CodeValidator) validateGo(code string) []ValidationError {
	var errors []ValidationError

	if !strings.Contains(code, "package ") {
		errors = append(errors, ValidationError{
			Line:    1,
			Message: "缺少 package 声明",
		})
	}

	braces := 0
	for _, ch := range code {
		switch ch {
		case '{':
			braces++
		case '}':
			braces--
		}
	}
	if braces != 0 {
		errors = append(errors, ValidationError{
			Line:    0,
			Message: "花括号不匹配",
		})
	}

	funcRegex := regexp.MustCompile(`func\s+\w+`)
	if !funcRegex.MatchString(code) {
		errors = append(errors, ValidationError{
			Line:    0,
			Message: "未找到函数定义",
		})
	}

	return errors
}

func (v *CodeValidator) validatePython(code string) []ValidationError {
	var errors []ValidationError

	classRegex := regexp.MustCompile(`class\s+\w+`)
	funcRegex := regexp.MustCompile(`def\s+\w+`)
	if !classRegex.MatchString(code) && !funcRegex.MatchString(code) {
		errors = append(errors, ValidationError{
			Line:    0,
			Message: "未找到类或函数定义",
		})
	}

	lines := strings.Split(code, "\n")
	for i, line := range lines {
		if len(line) > 0 && line[0] != ' ' && line[0] != '\t' && !strings.HasPrefix(line, "#") && !strings.HasPrefix(line, "from") && !strings.HasPrefix(line, "import") && !strings.HasPrefix(line, "class") && !strings.HasPrefix(line, "def") && !strings.HasPrefix(line, "@") && strings.TrimSpace(line) != "" {
			_ = i
		}
	}

	return errors
}

func (v *CodeValidator) validateTypeScript(code string) []ValidationError {
	var errors []ValidationError

	classRegex := regexp.MustCompile(`(class|interface|function|const|let|var)\s+\w+`)
	if !classRegex.MatchString(code) {
		errors = append(errors, ValidationError{
			Line:    0,
			Message: "未找到类、接口或函数定义",
		})
	}

	braces := 0
	for _, ch := range code {
		switch ch {
		case '{':
			braces++
		case '}':
			braces--
		}
	}
	if braces != 0 {
		errors = append(errors, ValidationError{
			Line:    0,
			Message: "花括号不匹配",
		})
	}

	return errors
}
