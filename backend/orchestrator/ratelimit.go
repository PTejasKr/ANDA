package main

import (
	"encoding/json"
	"net"
	"net/http"
	"strings"
	"sync"
	"time"
)

// Visitor tracks token bucket allocation for a specific IP
type Visitor struct {
	tokens     float64
	lastRefill time.Time
}

// IPRateLimiter implements a thread-safe token bucket limiter
type IPRateLimiter struct {
	mu           sync.RWMutex
	visitors     map[string]*Visitor
	ratePerSec   float64
	maxTokens    float64
	cleanupEvery time.Duration
}

// NewIPRateLimiter initializes a rate limiter with rate per minute and burst capacity
func NewIPRateLimiter(ratePerMinute int, burst int) *IPRateLimiter {
	limiter := &IPRateLimiter{
		visitors:     make(map[string]*Visitor),
		ratePerSec:   float64(ratePerMinute) / 60.0,
		maxTokens:    float64(burst),
		cleanupEvery: 2 * time.Minute,
	}
	go limiter.cleanupLoop()
	return limiter
}

func (l *IPRateLimiter) cleanupLoop() {
	ticker := time.NewTicker(l.cleanupEvery)
	for range ticker.C {
		l.mu.Lock()
		now := time.Now()
		for ip, v := range l.visitors {
			if now.Sub(v.lastRefill) > 5*time.Minute {
				delete(l.visitors, ip)
			}
		}
		l.mu.Unlock()
	}
}

// Allow checks if the request from ip is permitted
func (l *IPRateLimiter) Allow(ip string) bool {
	l.mu.Lock()
	defer l.mu.Unlock()

	now := time.Now()
	v, exists := l.visitors[ip]
	if !exists {
		l.visitors[ip] = &Visitor{
			tokens:     l.maxTokens - 1.0,
			lastRefill: now,
		}
		return true
	}

	elapsed := now.Sub(v.lastRefill).Seconds()
	v.lastRefill = now
	v.tokens += elapsed * l.ratePerSec
	if v.tokens > l.maxTokens {
		v.tokens = l.maxTokens
	}

	if v.tokens >= 1.0 {
		v.tokens -= 1.0
		return true
	}

	return false
}

// GetClientIP extracts client IP taking reverse proxy headers into account
func GetClientIP(r *http.Request) string {
	if xff := r.Header.Get("X-Forwarded-For"); xff != "" {
		parts := strings.Split(xff, ",")
		if len(parts) > 0 {
			ip := strings.TrimSpace(parts[0])
			if ip != "" {
				return ip
			}
		}
	}
	if xrip := r.Header.Get("X-Real-IP"); xrip != "" {
		return strings.TrimSpace(xrip)
	}
	host, _, err := net.SplitHostPort(r.RemoteAddr)
	if err == nil {
		return host
	}
	return r.RemoteAddr
}

// RateLimitMiddleware enforces rate limiting for an HTTP handler
func RateLimitMiddleware(limiter *IPRateLimiter, next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		ip := GetClientIP(r)
		if !limiter.Allow(ip) {
			w.Header().Set("Content-Type", "application/json")
			w.Header().Set("Retry-After", "30")
			w.WriteHeader(http.StatusTooManyRequests)
			json.NewEncoder(w).Encode(map[string]interface{}{
				"status":              429,
				"error":               "Rate limit exceeded. Too many requests from this client.",
				"retry_after_seconds": 30,
			})
			return
		}
		next(w, r)
	}
}
