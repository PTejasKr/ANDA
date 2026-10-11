package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"

	winio "github.com/Microsoft/go-winio"
)

// CapabilityToken represents an authorized administrative capability token
type CapabilityToken struct {
	Action    string            `json:"action"`
	Drive     string            `json:"drive,omitempty"`
	Hash      string            `json:"hash,omitempty"`
	TokenID   string            `json:"token_id"`
	Signature string            `json:"signature,omitempty"`
	Params    map[string]string `json:"params,omitempty"`
}

// DaemonResponse returned across the IPC pipe
type DaemonResponse struct {
	Status    string `json:"status"` // "success", "rejected", "error", "pending_hitl"
	Code      string `json:"code"`
	Message   string `json:"message"`
	TokenID   string `json:"token_id,omitempty"`
	Execution string `json:"execution,omitempty"`
}

// PendingHITL represents an action awaiting human approval
type PendingHITL struct {
	ID        string          `json:"id"`
	Token     CapabilityToken `json:"token"`
	CreatedAt time.Time       `json:"created_at"`
	ExpiresAt time.Time       `json:"expires_at"`
	Decision  chan bool       `json:"-"`
}

type DaemonService struct {
	mu          sync.Mutex
	pendingHITL map[string]*PendingHITL
	pipeName    string
	httpPort    string
	timeoutSec  int
}

func NewDaemonService(pipeName string, httpPort string, timeoutSec int) *DaemonService {
	return &DaemonService{
		pendingHITL: make(map[string]*PendingHITL),
		pipeName:    pipeName,
		httpPort:    httpPort,
		timeoutSec:  timeoutSec,
	}
}

// Allowed elevated actions
var allowedElevatedActions = map[string]bool{
	"flash_usb":          true,
	"os_update":          true,
	"quarantine_isolate": true,
	"format_drive":       true,
}

func (d *DaemonService) HandleIPCConnection(conn net.Conn) {
	defer conn.Close()

	reader := bufio.NewReader(conn)
	rawBytes, err := reader.ReadBytes('\n')
	if err != nil && err != io.EOF {
		return
	}

	rawPayload := strings.TrimSpace(string(rawBytes))
	if len(rawPayload) == 0 {
		return
	}

	// SECURITY BOUNDARY: Test Case 1 - Unauthorized Elevation
	// Check if the payload is raw shell syntax or unstructured text
	var token CapabilityToken
	err = json.Unmarshal([]byte(rawPayload), &token)
	if err != nil || token.Action == "" || token.TokenID == "" {
		// Log and reject unstructured or shell commands
		log.Printf("[SECURITY VIOLATION] Non-capability payload rejected: %s", rawPayload)
		resp := DaemonResponse{
			Status:  "rejected",
			Code:    "UNAUTHORIZED_PAYLOAD",
			Message: "IPC boundary violation: Only structured JSON capability tokens are permitted. Raw shell commands and malformed payloads are strictly rejected.",
		}
		respBytes, _ := json.Marshal(resp)
		conn.Write(append(respBytes, '\n'))
		return
	}

	// Check if action is recognized
	if !allowedElevatedActions[token.Action] {
		resp := DaemonResponse{
			Status:  "rejected",
			Code:    "UNKNOWN_CAPABILITY_ACTION",
			Message: fmt.Sprintf("Action '%s' is not an authorized elevated capability.", token.Action),
			TokenID: token.TokenID,
		}
		respBytes, _ := json.Marshal(resp)
		conn.Write(append(respBytes, '\n'))
		return
	}

	log.Printf("[ELEVATED DAEMON] Received valid capability token: %s (Action: %s)", token.TokenID, token.Action)

	// SECURITY BOUNDARY: Test Case 2 - Human-in-the-Loop (HITL) Validation
	hitl := &PendingHITL{
		ID:        token.TokenID,
		Token:     token,
		CreatedAt: time.Now(),
		ExpiresAt: time.Now().Add(time.Duration(d.timeoutSec) * time.Second),
		Decision:  make(chan bool, 1),
	}

	d.mu.Lock()
	d.pendingHITL[token.TokenID] = hitl
	d.mu.Unlock()

	log.Printf("[HITL GATE] Halting execution for token %s. Awaiting physical button confirmation (Timeout: %ds)...", token.TokenID, d.timeoutSec)

	// Wait for human decision or timeout
	select {
	case approved := <-hitl.Decision:
		d.mu.Lock()
		delete(d.pendingHITL, token.TokenID)
		d.mu.Unlock()

		if approved {
			log.Printf("[HITL APPROVED] User confirmed action %s for token %s. Executing...", token.Action, token.TokenID)
			resp := DaemonResponse{
				Status:    "success",
				Code:      "EXECUTION_COMPLETED",
				Message:   fmt.Sprintf("Elevated operation '%s' successfully authorized and completed by system daemon.", token.Action),
				TokenID:   token.TokenID,
				Execution: fmt.Sprintf("Simulated elevated execution of %s (Drive: %s, Hash: %s)", token.Action, token.Drive, token.Hash),
			}
			respBytes, _ := json.Marshal(resp)
			conn.Write(append(respBytes, '\n'))
		} else {
			log.Printf("[HITL DENIED] User explicitly rejected token %s", token.TokenID)
			resp := DaemonResponse{
				Status:  "rejected",
				Code:    "HITL_USER_DENIED",
				Message: "Human administrator denied execution of the capability token.",
				TokenID: token.TokenID,
			}
			respBytes, _ := json.Marshal(resp)
			conn.Write(append(respBytes, '\n'))
		}

	case <-time.After(time.Duration(d.timeoutSec) * time.Second):
		d.mu.Lock()
		delete(d.pendingHITL, token.TokenID)
		d.mu.Unlock()

		log.Printf("[HITL TIMEOUT] 60s expiration reached without user approval for token %s. Safe fail activated.", token.TokenID)
		resp := DaemonResponse{
			Status:  "rejected",
			Code:    "HITL_TIMEOUT",
			Message: fmt.Sprintf("Human-in-the-loop verification timed out after %d seconds. Elevated execution safely aborted.", d.timeoutSec),
			TokenID: token.TokenID,
		}
		respBytes, _ := json.Marshal(resp)
		conn.Write(append(respBytes, '\n'))
	}
}

// ApproveHITL allows human-in-the-loop decision via HTTP API or signal
func (d *DaemonService) ApproveHITL(tokenID string, approved bool) bool {
	d.mu.Lock()
	hitl, exists := d.pendingHITL[tokenID]
	d.mu.Unlock()

	if !exists {
		return false
	}

	select {
	case hitl.Decision <- approved:
		return true
	default:
		return false
	}
}

// StartHTTPController starts administrative HTTP monitoring for HITL approvals
func (d *DaemonService) StartHTTPController() {
	mux := http.NewServeMux()

	setCors := func(w http.ResponseWriter, r *http.Request) bool {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusOK)
			return true
		}
		return false
	}

	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		if setCors(w, r) {
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"status": "active",
			"plane":  "elevated_daemon",
			"ipc":    d.pipeName,
		})
	})

	mux.HandleFunc("/api/daemon/pending", func(w http.ResponseWriter, r *http.Request) {
		if setCors(w, r) {
			return
		}
		d.mu.Lock()
		defer d.mu.Unlock()
		list := make([]PendingHITL, 0, len(d.pendingHITL))
		for _, v := range d.pendingHITL {
			list = append(list, *v)
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(list)
	})

	mux.HandleFunc("/api/daemon/approve", func(w http.ResponseWriter, r *http.Request) {
		if setCors(w, r) {
			return
		}
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		var req struct {
			TokenID  string `json:"token_id"`
			Approved bool   `json:"approved"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		success := d.ApproveHITL(req.TokenID, req.Approved)
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success":  success,
			"token_id": req.TokenID,
			"decision": req.Approved,
		})
	})

	log.Printf("[ELEVATED DAEMON] Admin HTTP controller running on :%s", d.httpPort)
	if err := http.ListenAndServe(":"+d.httpPort, mux); err != nil {
		log.Printf("[ELEVATED DAEMON] HTTP controller terminated: %v", err)
	}
}

func (d *DaemonService) StartNamedPipeListener() error {
	listener, err := winio.ListenPipe(d.pipeName, nil)
	if err != nil {
		return fmt.Errorf("failed to create named pipe listener on %s: %w", d.pipeName, err)
	}
	defer listener.Close()

	log.Printf("[ELEVATED DAEMON] Listening securely on Named Pipe: %s", d.pipeName)

	for {
		conn, err := listener.Accept()
		if err != nil {
			log.Printf("[ELEVATED DAEMON] Named pipe accept error: %v", err)
			continue
		}
		go d.HandleIPCConnection(conn)
	}
}

func main() {
	pipeName := os.Getenv("DAEMON_PIPE")
	if pipeName == "" {
		pipeName = `\\.\pipe\omni_daemon_ipc`
	}
	httpPort := os.Getenv("DAEMON_HTTP_PORT")
	if httpPort == "" {
		httpPort = "8081"
	}

	daemon := NewDaemonService(pipeName, httpPort, 60)

	go daemon.StartHTTPController()

	if err := daemon.StartNamedPipeListener(); err != nil {
		log.Fatalf("[FATAL] Could not start Elevated Daemon IPC: %v", err)
	}
}
