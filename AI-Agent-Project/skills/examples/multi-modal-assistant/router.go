package main

import (
	"strings"
)

type Intent struct {
	Name       string  `json:"name"`
	Confidence float64 `json:"confidence"`
}

type IntentHandler func(input *AssistantInput, ctx *Session) (*AssistantOutput, error)

type IntentRoute struct {
	Intent   Intent
	Handler  IntentHandler
	Keywords []string
}

type IntentRouter struct {
	routes    []IntentRoute
	threshold float64
}

func NewIntentRouter(threshold float64) *IntentRouter {
	return &IntentRouter{
		routes:    make([]IntentRoute, 0),
		threshold: threshold,
	}
}

func (r *IntentRouter) RegisterRoute(name string, keywords []string, handler IntentHandler) {
	r.routes = append(r.routes, IntentRoute{
		Intent:   Intent{Name: name},
		Handler:  handler,
		Keywords: keywords,
	})
}

func (r *IntentRouter) Route(input *AssistantInput) (*IntentRoute, error) {
	bestMatch := IntentRoute{}
	bestScore := 0.0

	message := strings.ToLower(input.Message)

	for _, route := range r.routes {
		score := r.matchScore(message, route.Keywords)
		if input.Modality == "image" && route.Intent.Name == "image_analysis" {
			score = max(score, 0.9)
		}
		if input.Modality == "audio" && route.Intent.Name == "audio_transcription" {
			score = max(score, 0.9)
		}

		if score > bestScore {
			bestScore = score
			bestMatch = route
		}
	}

	if bestScore < r.threshold {
		for _, route := range r.routes {
			if route.Intent.Name == "general" {
				return &route, nil
			}
		}
		return nil, nil
	}

	bestMatch.Intent.Confidence = bestScore
	return &bestMatch, nil
}

func (r *IntentRouter) matchScore(message string, keywords []string) float64 {
	if len(keywords) == 0 {
		return 0
	}

	matched := 0
	for _, kw := range keywords {
		if strings.Contains(message, strings.ToLower(kw)) {
			matched++
		}
	}

	return float64(matched) / float64(len(keywords))
}

func max(a, b float64) float64 {
	if a > b {
		return a
	}
	return b
}
