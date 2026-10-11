package main

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestIPRateLimiter_AllowAndBlock(t *testing.T) {
	// 5 requests per minute, burst capacity of 3
	limiter := NewIPRateLimiter(5, 3)
	ip := "192.168.1.100"

	// First 3 requests should pass (burst)
	for i := 0; i < 3; i++ {
		if !limiter.Allow(ip) {
			t.Fatalf("Expected request %d to be allowed under burst capacity", i+1)
		}
	}

	// 4th immediate request should be rejected
	if limiter.Allow(ip) {
		t.Fatalf("Expected 4th immediate request to be blocked by rate limiter")
	}

	// Different IP should still be allowed
	otherIP := "192.168.1.101"
	if !limiter.Allow(otherIP) {
		t.Fatalf("Expected different IP to be allowed")
	}
}

func TestRateLimitMiddleware_HTTPStatus429(t *testing.T) {
	limiter := NewIPRateLimiter(2, 2)
	handler := RateLimitMiddleware(limiter, func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("ok"))
	})

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	req.RemoteAddr = "10.0.0.1:12345"

	// Request 1: OK
	rec1 := httptest.NewRecorder()
	handler(rec1, req)
	if rec1.Code != http.StatusOK {
		t.Errorf("Expected 200, got %d", rec1.Code)
	}

	// Request 2: OK
	rec2 := httptest.NewRecorder()
	handler(rec2, req)
	if rec2.Code != http.StatusOK {
		t.Errorf("Expected 200, got %d", rec2.Code)
	}

	// Request 3: 429 Too Many Requests
	rec3 := httptest.NewRecorder()
	handler(rec3, req)
	if rec3.Code != http.StatusTooManyRequests {
		t.Errorf("Expected 429 Too Many Requests, got %d", rec3.Code)
	}
	if rec3.Header().Get("Retry-After") != "30" {
		t.Errorf("Expected Retry-After header to be 30, got %s", rec3.Header().Get("Retry-After"))
	}
}

func TestGetClientIP_XForwardedFor(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	req.RemoteAddr = "127.0.0.1:8080"
	req.Header.Set("X-Forwarded-For", "203.0.113.195, 70.41.3.18")

	ip := GetClientIP(req)
	if ip != "203.0.113.195" {
		t.Errorf("Expected 203.0.113.195, got %s", ip)
	}
}
