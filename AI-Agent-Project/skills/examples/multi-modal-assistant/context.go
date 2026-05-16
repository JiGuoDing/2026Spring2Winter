package main

import "sync"

type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
	Modality string `json:"modality,omitempty"`
}

type Session struct {
	ID       string    `json:"id"`
	Messages []Message `json:"messages"`
	Metadata map[string]interface{} `json:"metadata,omitempty"`
}

type ContextManager struct {
	sessions map[string]*Session
	mu       sync.RWMutex
	maxTurns int
}

func NewContextManager(maxTurns int) *ContextManager {
	return &ContextManager{
		sessions: make(map[string]*Session),
		maxTurns: maxTurns,
	}
}

func (cm *ContextManager) GetOrCreateSession(sessionID string) *Session {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	if session, exists := cm.sessions[sessionID]; exists {
		return session
	}

	session := &Session{
		ID:       sessionID,
		Messages: make([]Message, 0),
		Metadata: make(map[string]interface{}),
	}
	cm.sessions[sessionID] = session
	return session
}

func (cm *ContextManager) AddMessage(sessionID string, msg Message) {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	session, exists := cm.sessions[sessionID]
	if !exists {
		return
	}

	session.Messages = append(session.Messages, msg)
	if cm.maxTurns > 0 && len(session.Messages) > cm.maxTurns*2 {
		session.Messages = session.Messages[2:]
	}
}

func (cm *ContextManager) GetHistory(sessionID string) []Message {
	cm.mu.RLock()
	defer cm.mu.RUnlock()

	session, exists := cm.sessions[sessionID]
	if !exists {
		return nil
	}

	history := make([]Message, len(session.Messages))
	copy(history, session.Messages)
	return history
}

func (cm *ContextManager) ClearSession(sessionID string) {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	delete(cm.sessions, sessionID)
}

func (cm *ContextManager) SessionCount() int {
	cm.mu.RLock()
	defer cm.mu.RUnlock()
	return len(cm.sessions)
}
