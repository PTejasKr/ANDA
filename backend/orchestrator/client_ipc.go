package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"
)

type IPCClient struct {
	pipeName       string
	daemonHTTPHost string
}

func NewIPCClient(pipeName string, daemonHTTPHost string) *IPCClient {
	if pipeName == "" {
		pipeName = `\\.\pipe\omni_daemon_ipc`
	}
	if daemonHTTPHost == "" {
		daemonHTTPHost = "http://127.0.0.1:8081"
	}
	return &IPCClient{
		pipeName:       pipeName,
		daemonHTTPHost: daemonHTTPHost,
	}
}

// SendRawPayload sends arbitrary text across the named pipe (used in Test Case 1)
func (c *IPCClient) SendRawPayload(raw string) (string, error) {
	timeout := 5 * time.Second
	conn, err := dialIPCConn(c.pipeName, timeout)
	if err != nil {
		return "", fmt.Errorf("failed to dial named pipe %s: %w", c.pipeName, err)
	}
	defer conn.Close()

	if !strings.HasSuffix(raw, "\n") {
		raw += "\n"
	}

	_, err = conn.Write([]byte(raw))
	if err != nil {
		return "", fmt.Errorf("write error: %w", err)
	}

	reader := bufio.NewReader(conn)
	resp, err := reader.ReadString('\n')
	if err != nil {
		return "", fmt.Errorf("read error: %w", err)
	}
	return strings.TrimSpace(resp), nil
}

// SendCapabilityToken sends a valid structured capability token over the named pipe
func (c *IPCClient) SendCapabilityToken(token map[string]interface{}) (map[string]interface{}, error) {
	bytesData, err := json.Marshal(token)
	if err != nil {
		return nil, err
	}

	rawResp, err := c.SendRawPayload(string(bytesData))
	if err != nil {
		return nil, err
	}

	var parsed map[string]interface{}
	if err := json.Unmarshal([]byte(rawResp), &parsed); err != nil {
		return map[string]interface{}{
			"status":   "raw",
			"response": rawResp,
		}, nil
	}
	return parsed, nil
}

// FetchPendingHITL queries the Daemon's HITL queue
func (c *IPCClient) FetchPendingHITL() ([]map[string]interface{}, error) {
	resp, err := http.Get(c.daemonHTTPHost + "/api/daemon/pending")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var list []map[string]interface{}
	err = json.NewDecoder(resp.Body).Decode(&list)
	return list, err
}

// SubmitHITLDecision sends the human approval or rejection to the Daemon
func (c *IPCClient) SubmitHITLDecision(tokenID string, approved bool) (bool, error) {
	payload, _ := json.Marshal(map[string]interface{}{
		"token_id": tokenID,
		"approved": approved,
	})

	resp, err := http.Post(c.daemonHTTPHost+"/api/daemon/approve", "application/json", bytes.NewReader(payload))
	if err != nil {
		return false, err
	}
	defer resp.Body.Close()

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return false, err
	}

	success, _ := result["success"].(bool)
	return success, nil
}
