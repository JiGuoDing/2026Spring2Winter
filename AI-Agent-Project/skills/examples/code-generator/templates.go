package main

import (
	"bytes"
	"text/template"
)

type TemplateVars map[string]interface{}

type CodeTemplate struct {
	Name     string
	Language string
	Content  string
}

type TemplateManager struct {
	templates map[string][]CodeTemplate
}

func NewTemplateManager() *TemplateManager {
	tm := &TemplateManager{
		templates: make(map[string][]CodeTemplate),
	}
	tm.registerDefaults()
	return tm
}

func (tm *TemplateManager) Register(name, language, content string) {
	ct := CodeTemplate{
		Name:     name,
		Language: language,
		Content:  content,
	}
	tm.templates[name] = append(tm.templates[name], ct)
}

func (tm *TemplateManager) Get(name, language string) (*CodeTemplate, bool) {
	templates, exists := tm.templates[name]
	if !exists {
		return nil, false
	}

	for _, t := range templates {
		if t.Language == language {
			return &t, true
		}
	}

	if len(templates) > 0 {
		return &templates[0], true
	}
	return nil, false
}

func (tm *TemplateManager) Execute(name, language string, vars TemplateVars) (string, error) {
	ct, exists := tm.Get(name, language)
	if !exists {
		return "", nil
	}

	tmpl, err := template.New(name).Parse(ct.Content)
	if err != nil {
		return "", err
	}

	var buf bytes.Buffer
	if err := tmpl.Execute(&buf, vars); err != nil {
		return "", err
	}

	return buf.String(), nil
}

func (tm *TemplateManager) ListTemplates() []string {
	names := make([]string, 0, len(tm.templates))
	for name := range tm.templates {
		names = append(names, name)
	}
	return names
}

func (tm *TemplateManager) registerDefaults() {
	tm.Register("handler", "go", `package {{.Package}}

type {{.HandlerName}}Handler struct{}

func New{{.HandlerName}}Handler() *{{.HandlerName}}Handler {
	return &{{.HandlerName}}Handler{}
}

func (h *{{.HandlerName}}Handler) Handle(input json.RawMessage) (json.RawMessage, error) {
	return nil, nil
}
`)

	tm.Register("handler", "python", `class {{.HandlerName}}Handler:
    def __init__(self):
        pass

    def handle(self, input_data):
        raise NotImplementedError
`)

	tm.Register("handler", "typescript", `export class {{.HandlerName}}Handler {
  constructor() {}

  async handle(input: any): Promise<any> {
    throw new Error('Not implemented');
  }
}
`)

	tm.Register("model", "go", `package {{.Package}}

type {{.ModelName}} struct {
{{range .Fields}}	{{.Name}} {{.Type}} ` + "`json:\"{{.JSONTag}}\"`" + `
{{end}}
}
`)

	tm.Register("model", "python", `from dataclasses import dataclass
from typing import Optional

@dataclass
class {{.ModelName}}:
{{range .Fields}}    {{.Name}}: {{.Type}}
{{end}}
`)

	tm.Register("api", "go", `package {{.Package}}

import (
	"encoding/json"
	"net/http"
)

func {{.HandlerName}}Handler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}
`)

	tm.Register("api", "python", `from fastapi import APIRouter

router = APIRouter()

@router.{{.Method | lower}}("{{.Path}}")
async def {{.HandlerName | lower}}():
    return {"status": "ok"}
`)

	tm.Register("api", "typescript", `import { Router } from 'express';

const router = Router();

router.{{.Method | lower}}('{{.Path}}', async (req, res) => {
  res.json({ status: 'ok' });
});

export default router;
`)
}
