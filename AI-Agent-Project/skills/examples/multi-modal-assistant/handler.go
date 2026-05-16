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

type AssistantInput struct {
	Message   string `json:"message"`
	Modality  string `json:"modality,omitempty"`
	ImageURL  string `json:"image_url,omitempty"`
	AudioURL  string `json:"audio_url,omitempty"`
	SessionID string `json:"session_id"`
	Stream    bool   `json:"stream,omitempty"`
}

type AssistantOutput struct {
	Response  string   `json:"response"`
	Intent    string   `json:"intent"`
	Confidence float64 `json:"confidence"`
	Modality  string   `json:"modality,omitempty"`
	SubSkills []string `json:"sub_skills,omitempty"`
}

type MultiModalHandler struct {
	router  *IntentRouter
	context *ContextManager
}

func NewMultiModalHandler(router *IntentRouter, ctx *ContextManager) *MultiModalHandler {
	return &MultiModalHandler{
		router:  router,
		context: ctx,
	}
}

func (h *MultiModalHandler) Validate(input json.RawMessage) error {
	var in AssistantInput
	if err := json.Unmarshal(input, &in); err != nil {
		return &SkillError{
			Code:    "INVALID_INPUT",
			Message: "无法解析输入参数",
			Detail:  err.Error(),
		}
	}

	if in.Message == "" && in.Modality != "image" && in.Modality != "audio" {
		return &SkillError{
			Code:    "EMPTY_MESSAGE",
			Message: "消息内容不能为空",
		}
	}

	if in.SessionID == "" {
		return &SkillError{
			Code:    "MISSING_SESSION",
			Message: "会话ID不能为空",
		}
	}

	validModalities := map[string]bool{"text": true, "image": true, "audio": true, "": true}
	if !validModalities[in.Modality] {
		return &SkillError{
			Code:    "INVALID_MODALITY",
			Message: "不支持的模态类型",
			Detail:  fmt.Sprintf("modality=%s", in.Modality),
		}
	}

	return nil
}

func (h *MultiModalHandler) Handle(input json.RawMessage) (json.RawMessage, error) {
	if err := h.Validate(input); err != nil {
		return nil, err
	}

	var in AssistantInput
	_ = json.Unmarshal(input, &in)

	if in.Modality == "" {
		in.Modality = "text"
	}

	session := h.context.GetOrCreateSession(in.SessionID)
	h.context.AddMessage(in.SessionID, Message{
		Role:     "user",
		Content:  in.Message,
		Modality: in.Modality,
	})

	route, err := h.router.Route(&in)
	if err != nil {
		return nil, &SkillError{
			Code:    "ROUTING_ERROR",
			Message: "意图路由失败",
			Detail:  err.Error(),
		}
	}
	if route == nil {
		return nil, &SkillError{
			Code:    "NO_ROUTE",
			Message: "无法匹配意图",
		}
	}

	output, err := route.Handler(&in, session)
	if err != nil {
		return nil, &SkillError{
			Code:    "HANDLER_ERROR",
			Message: "子技能执行失败",
			Detail:  fmt.Sprintf("intent=%s, error=%v", route.Intent.Name, err),
		}
	}

	output.Intent = route.Intent.Name
	output.Confidence = route.Intent.Confidence
	output.Modality = "text"

	h.context.AddMessage(in.SessionID, Message{
		Role:    "assistant",
		Content: output.Response,
	})

	return json.Marshal(output)
}

func RegisterDefaultRoutes(router *IntentRouter) {
	router.RegisterRoute("greeting", []string{"你好", "hello", "嗨", "hi", "早上好"}, func(input *AssistantInput, _ *Session) (*AssistantOutput, error) {
		return &AssistantOutput{
			Response:  fmt.Sprintf("你好！我是多模态助手，有什么可以帮助你的吗？"),
			SubSkills: []string{"greeting"},
		}, nil
	})

	router.RegisterRoute("question", []string{"什么是", "如何", "为什么", "怎么", "how", "what", "why"}, func(input *AssistantInput, _ *Session) (*AssistantOutput, error) {
		return &AssistantOutput{
			Response:  fmt.Sprintf("关于你的问题「%s」，让我为你查找相关信息...", input.Message),
			SubSkills: []string{"question", "search"},
		}, nil
	})

	router.RegisterRoute("image_analysis", []string{"图片", "照片", "image", "picture", "看看"}, func(input *AssistantInput, _ *Session) (*AssistantOutput, error) {
		imageDesc := "图片"
		if input.ImageURL != "" {
			imageDesc = input.ImageURL
		}
		return &AssistantOutput{
			Response:  fmt.Sprintf("正在分析图片: %s", imageDesc),
			SubSkills: []string{"image_analysis", "vision"},
		}, nil
	})

	router.RegisterRoute("audio_transcription", []string{"语音", "录音", "audio", "voice"}, func(input *AssistantInput, _ *Session) (*AssistantOutput, error) {
		return &AssistantOutput{
			Response:  "正在处理语音输入...",
			SubSkills: []string{"audio_transcription", "speech_to_text"},
		}, nil
	})

	router.RegisterRoute("code_help", []string{"代码", "编程", "code", "program", "debug"}, func(input *AssistantInput, _ *Session) (*AssistantOutput, error) {
		return &AssistantOutput{
			Response:  fmt.Sprintf("关于编程问题「%s」，让我帮你分析...", input.Message),
			SubSkills: []string{"code_help", "analysis"},
		}, nil
	})

	router.RegisterRoute("general", []string{}, func(input *AssistantInput, _ *Session) (*AssistantOutput, error) {
		return &AssistantOutput{
			Response:  fmt.Sprintf("收到你的消息：「%s」，我会尽力帮助你。", input.Message),
			SubSkills: []string{"general"},
		}, nil
	})
}
