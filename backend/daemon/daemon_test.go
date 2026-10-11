package main

import (
	"bufio"
	"encoding/json"
	"strings"
	"testing"
	"time"

	winio "github.com/Microsoft/go-winio"
)

func startTestDaemon(pipeName string, timeoutSec int) (*DaemonService, func(), error) {
	daemon := NewDaemonService(pipeName, "0", timeoutSec)

	listener, err := winio.ListenPipe(pipeName, nil)
	if err != nil {
		return nil, nil, err
	}

	stopChan := make(chan struct{})
	go func() {
		for {
			conn, err := listener.Accept()
			if err != nil {
				select {
				case <-stopChan:
					return
				default:
					continue
				}
			}
			go daemon.HandleIPCConnection(conn)
		}
	}()

	cleanup := func() {
		close(stopChan)
		listener.Close()
	}

	return daemon, cleanup, nil
}

// Test Case 1: Unauthorized Elevation - Reject raw shell commands
func TestIPCUnauthorizedElevation(t *testing.T) {
	pipeName := `\\.\pipe\omni_test_pipe_unauth`
	_, cleanup, err := startTestDaemon(pipeName, 5)
	if err != nil {
		t.Fatalf("failed to start test daemon: %v", err)
	}
	defer cleanup()

	dialTimeout := 2 * time.Second
	conn, err := winio.DialPipe(pipeName, &dialTimeout)
	if err != nil {
		t.Fatalf("failed to dial named pipe: %v", err)
	}
	defer conn.Close()

	// Attempt raw shell injection
	rawAttack := "cmd.exe /c whoami && echo pwned\n"
	_, err = conn.Write([]byte(rawAttack))
	if err != nil {
		t.Fatalf("failed to write raw payload: %v", err)
	}

	reader := bufio.NewReader(conn)
	respStr, err := reader.ReadString('\n')
	if err != nil {
		t.Fatalf("failed to read daemon response: %v", err)
	}

	var resp DaemonResponse
	if err := json.Unmarshal([]byte(strings.TrimSpace(respStr)), &resp); err != nil {
		t.Fatalf("failed to parse daemon response JSON: %v", err)
	}

	if resp.Status != "rejected" {
		t.Errorf("expected status 'rejected', got '%s'", resp.Status)
	}
	if resp.Code != "UNAUTHORIZED_PAYLOAD" {
		t.Errorf("expected code 'UNAUTHORIZED_PAYLOAD', got '%s'", resp.Code)
	}
}

// Test Case 2: Human-in-the-Loop Validation - Timeout Fails Safely
func TestIPCHITLTimeoutSafeFail(t *testing.T) {
	pipeName := `\\.\pipe\omni_test_pipe_timeout`
	// Fast 1 second timeout for test speed
	_, cleanup, err := startTestDaemon(pipeName, 1)
	if err != nil {
		t.Fatalf("failed to start test daemon: %v", err)
	}
	defer cleanup()

	dialTimeout := 2 * time.Second
	conn, err := winio.DialPipe(pipeName, &dialTimeout)
	if err != nil {
		t.Fatalf("failed to dial named pipe: %v", err)
	}
	defer conn.Close()

	token := CapabilityToken{
		Action:  "flash_usb",
		Drive:   "E:",
		Hash:    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
		TokenID: "token-timeout-test-1",
	}
	tokenBytes, _ := json.Marshal(token)
	tokenBytes = append(tokenBytes, '\n')

	_, err = conn.Write(tokenBytes)
	if err != nil {
		t.Fatalf("failed to write capability token: %v", err)
	}

	// Execution should halt, then after 1s timeout fail safely
	reader := bufio.NewReader(conn)
	respStr, err := reader.ReadString('\n')
	if err != nil {
		t.Fatalf("failed to read daemon response: %v", err)
	}

	var resp DaemonResponse
	if err := json.Unmarshal([]byte(strings.TrimSpace(respStr)), &resp); err != nil {
		t.Fatalf("failed to parse response JSON: %v", err)
	}

	if resp.Status != "rejected" {
		t.Errorf("expected status 'rejected', got '%s'", resp.Status)
	}
	if resp.Code != "HITL_TIMEOUT" {
		t.Errorf("expected code 'HITL_TIMEOUT', got '%s'", resp.Code)
	}
}

// Test Case 2 (Approved): Human-in-the-Loop Validation - User Confirmation Signal
func TestIPCHITLApprovedExecution(t *testing.T) {
	pipeName := `\\.\pipe\omni_test_pipe_approve`
	daemon, cleanup, err := startTestDaemon(pipeName, 5)
	if err != nil {
		t.Fatalf("failed to start test daemon: %v", err)
	}
	defer cleanup()

	dialTimeout := 2 * time.Second
	conn, err := winio.DialPipe(pipeName, &dialTimeout)
	if err != nil {
		t.Fatalf("failed to dial named pipe: %v", err)
	}
	defer conn.Close()

	tokenID := "token-approve-test-2"
	token := CapabilityToken{
		Action:  "flash_usb",
		Drive:   "E:",
		Hash:    "f865b53623b121fd34ee5426c792e5c33af8c227",
		TokenID: tokenID,
	}
	tokenBytes, _ := json.Marshal(token)
	tokenBytes = append(tokenBytes, '\n')

	_, err = conn.Write(tokenBytes)
	if err != nil {
		t.Fatalf("failed to write token: %v", err)
	}

	// Simulate human physical button approval signal after 200ms
	go func() {
		time.Sleep(200 * time.Millisecond)
		daemon.ApproveHITL(tokenID, true)
	}()

	reader := bufio.NewReader(conn)
	respStr, err := reader.ReadString('\n')
	if err != nil {
		t.Fatalf("failed to read daemon response: %v", err)
	}

	var resp DaemonResponse
	if err := json.Unmarshal([]byte(strings.TrimSpace(respStr)), &resp); err != nil {
		t.Fatalf("failed to parse response: %v", err)
	}

	if resp.Status != "success" {
		t.Errorf("expected status 'success', got '%s'", resp.Status)
	}
	if resp.Code != "EXECUTION_COMPLETED" {
		t.Errorf("expected code 'EXECUTION_COMPLETED', got '%s'", resp.Code)
	}
}
