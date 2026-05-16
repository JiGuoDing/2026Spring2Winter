package main

import (
	"sync"
	"time"
)

type CacheItem struct {
	Value      interface{}
	ExpireAt   time.Time
}

type MemoryCache struct {
	items map[string]*CacheItem
	mu    sync.RWMutex
	ttl   time.Duration
}

func NewMemoryCache(ttl time.Duration) *MemoryCache {
	c := &MemoryCache{
		items: make(map[string]*CacheItem),
		ttl:   ttl,
	}
	go c.cleanup()
	return c
}

func (c *MemoryCache) Get(key string) (interface{}, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	item, exists := c.items[key]
	if !exists {
		return nil, false
	}
	if time.Now().After(item.ExpireAt) {
		return nil, false
	}
	return item.Value, true
}

func (c *MemoryCache) Set(key string, value interface{}) {
	c.mu.Lock()
	defer c.mu.Unlock()

	c.items[key] = &CacheItem{
		Value:    value,
		ExpireAt: time.Now().Add(c.ttl),
	}
}

func (c *MemoryCache) Delete(key string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	delete(c.items, key)
}

func (c *MemoryCache) cleanup() {
	ticker := time.NewTicker(time.Minute)
	defer ticker.Stop()

	for range ticker.C {
		c.mu.Lock()
		now := time.Now()
		for key, item := range c.items {
			if now.After(item.ExpireAt) {
				delete(c.items, key)
			}
		}
		c.mu.Unlock()
	}
}
