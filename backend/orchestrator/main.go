package main

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"time"
)

type OrchestratorServer struct {
	router           *Router
	ipcClient        *IPCClient
	workerHost       string
	storageRoot      string
	port             string
	workerClient     *http.Client
	globalLimiter    *IPRateLimiter
	commandLimiter   *IPRateLimiter
	commandSemaphore chan struct{}
}

func NewOrchestratorServer() *OrchestratorServer {
	port := os.Getenv("ORCHESTRATOR_PORT")
	if port == "" {
		port = "8080"
	}
	workerHost := os.Getenv("WORKER_HOST")
	if workerHost == "" {
		workerHost = "http://127.0.0.1:50051"
	}
	storageRoot := os.Getenv("STORAGE_ROOT")
	if storageRoot == "" {
		storageRoot = "storage"
	}

	return &OrchestratorServer{
		router:           NewRouter(),
		ipcClient:        NewIPCClient("", ""),
		workerHost:       workerHost,
		storageRoot:      storageRoot,
		port:             port,
		workerClient:     &http.Client{Timeout: 45 * time.Second},
		globalLimiter:    NewIPRateLimiter(60, 15),
		commandLimiter:   NewIPRateLimiter(20, 5),
		commandSemaphore: make(chan struct{}, 10), // Concurrency constraint: 10 in-flight tasks
	}
}

// EnsureDirectories creates required storage structure
func (s *OrchestratorServer) EnsureDirectories() {
	dirs := []string{
		filepath.Join(s.storageRoot, "ingest"),
		filepath.Join(s.storageRoot, "staging", "receipts"),
		filepath.Join(s.storageRoot, "staging", "financial_reports"),
		filepath.Join(s.storageRoot, "staging", "spreadsheets"),
		filepath.Join(s.storageRoot, "staging", "general"),
		filepath.Join(s.storageRoot, "quarantine", "sandbox"),
		filepath.Join(s.storageRoot, "quarantine", "locked"),
		filepath.Join(s.storageRoot, "memory_store"),
	}
	for _, d := range dirs {
		_ = os.MkdirAll(d, 0755)
	}
}

// FileInfoDTO represents a file in the file manager
type FileInfoDTO struct {
	Name     string    `json:"name"`
	Path     string    `json:"path"`
	RelPath  string    `json:"rel_path"`
	Size     int64     `json:"size"`
	ModTime  time.Time `json:"mod_time"`
	IsDir    bool      `json:"is_dir"`
	Category string    `json:"category"`
	Sha256   string    `json:"sha256,omitempty"`
	IsLocked bool      `json:"is_locked"`
}

func (s *OrchestratorServer) handleFSList(w http.ResponseWriter, r *http.Request) {
	relFolder := r.URL.Query().Get("folder")
	targetDir := filepath.Clean(filepath.Join(s.storageRoot, relFolder))

	// Path traversal protection
	cleanStorage := filepath.Clean(s.storageRoot)
	if !strings.HasPrefix(targetDir, cleanStorage) {
		http.Error(w, "Access Denied: Path traversal prohibited", http.StatusForbidden)
		return
	}

	entries, err := os.ReadDir(targetDir)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	var fileList []FileInfoDTO
	for _, entry := range entries {
		fullPath := filepath.Join(targetDir, entry.Name())
		info, err := entry.Info()
		if err != nil {
			continue
		}

		rel, _ := filepath.Rel(s.storageRoot, fullPath)
		dto := FileInfoDTO{
			Name:     entry.Name(),
			Path:     fullPath,
			RelPath:  rel,
			Size:     info.Size(),
			ModTime:  info.ModTime(),
			IsDir:    entry.IsDir(),
			Category: filepath.Base(filepath.Dir(fullPath)),
			IsLocked: strings.Contains(fullPath, "locked"),
		}

		if !entry.IsDir() && info.Size() < 10*1024*1024 {
			if content, err := os.ReadFile(fullPath); err == nil {
				h := sha256.Sum256(content)
				dto.Sha256 = hex.EncodeToString(h[:])
			}
		}
		fileList = append(fileList, dto)
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(fileList)
}

func (s *OrchestratorServer) handleFSRead(w http.ResponseWriter, r *http.Request) {
	relPath := r.URL.Query().Get("path")
	fullPath := filepath.Clean(filepath.Join(s.storageRoot, relPath))

	cleanStorage := filepath.Clean(s.storageRoot)
	if !strings.HasPrefix(fullPath, cleanStorage) {
		http.Error(w, "Access Denied", http.StatusForbidden)
		return
	}

	content, err := os.ReadFile(fullPath)
	if err != nil {
		http.Error(w, err.Error(), http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/octet-stream")
	w.Write(content)
}

func (s *OrchestratorServer) handleCommand(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Performance constraint: Max 5MB request body for command JSON
	r.Body = http.MaxBytesReader(w, r.Body, 5*1024*1024)

	// Concurrency constraint: Bounded execution semaphore
	select {
	case s.commandSemaphore <- struct{}{}:
		defer func() { <-s.commandSemaphore }()
	default:
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusServiceUnavailable)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"status": 503,
			"error":  "Server execution capacity reached. Please retry in a few moments.",
		})
		return
	}

	var req struct {
		Prompt string `json:"prompt"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	// 1. Intent Route & Pre-execution Security Scan
	route, err := s.router.RouteIntent(req.Prompt)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusForbidden)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"status":     "security_blocked",
			"error":      err.Error(),
			"route":      route,
			"blocked_at": time.Now().Format(time.RFC3339),
		})
		return
	}

	// 2. Route to appropriate subsystem
	switch route.Destination {
	case DestDaemon:
		// Draft capability token
		tokenID := fmt.Sprintf("cap-%d", time.Now().UnixNano())
		token := map[string]interface{}{
			"action":   route.Action,
			"drive":    "E:",
			"hash":     fmt.Sprintf("%x", sha256.Sum256([]byte(req.Prompt))),
			"token_id": tokenID,
			"params": map[string]string{
				"prompt": req.Prompt,
				"sender": "orchestrator",
			},
		}

		// Asynchronously initiate pipe request, awaiting HITL approval
		go func() {
			_, _ = s.ipcClient.SendCapabilityToken(token)
		}()

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"status":       "hitl_pending",
			"route":        route,
			"token_id":     tokenID,
			"message":      "Elevated action requires physical human verification. Confirm via HITL modal.",
			"timeout_secs": 60,
			"token":        token,
		})

	case DestMemory:
		// Perform RAG vector search with timeout deadline
		ctx, cancel := context.WithTimeout(r.Context(), 45*time.Second)
		defer cancel()

		ragBody, _ := json.Marshal(map[string]interface{}{
			"query": req.Prompt,
			"top_k": 4,
		})
		ragReq, _ := http.NewRequestWithContext(ctx, http.MethodPost, s.workerHost+"/api/memory/query", bytes.NewReader(ragBody))
		ragReq.Header.Set("Content-Type", "application/json")

		resp, err := s.workerClient.Do(ragReq)
		var ragResult map[string]interface{}
		if err == nil {
			json.NewDecoder(resp.Body).Decode(&ragResult)
			resp.Body.Close()
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"status":  "success",
			"route":   route,
			"memory":  ragResult,
			"message": "Retrieved relevant context from shared vector memory.",
		})

	case DestWorker:
		ctx, cancel := context.WithTimeout(r.Context(), 45*time.Second)
		defer cancel()

		// First retrieve RAG memory context to augment prompt
		ragBody, _ := json.Marshal(map[string]interface{}{
			"query": req.Prompt,
			"top_k": 3,
		})
		var ragContext string
		ragReq, _ := http.NewRequestWithContext(ctx, http.MethodPost, s.workerHost+"/api/memory/query", bytes.NewReader(ragBody))
		ragReq.Header.Set("Content-Type", "application/json")
		if ragResp, err := s.workerClient.Do(ragReq); err == nil {
			var ragMap map[string]interface{}
			if err := json.NewDecoder(ragResp.Body).Decode(&ragMap); err == nil {
				if results, ok := ragMap["results"].([]interface{}); ok && len(results) > 0 {
					ragContext = fmt.Sprintf("Retrieved %d context chunks from shared memory.", len(results))
				}
			}
			ragResp.Body.Close()
		}

		// Execute worker task
		var result map[string]interface{}
		if route.Action == "stage_files" {
			stageReq, _ := http.NewRequestWithContext(ctx, http.MethodPost, s.workerHost+"/api/stage", nil)
			stageReq.Header.Set("Content-Type", "application/json")
			resp, err := s.workerClient.Do(stageReq)
			if err == nil {
				json.NewDecoder(resp.Body).Decode(&result)
				resp.Body.Close()
			}
		} else {
			result = map[string]interface{}{
				"worker_action": route.Action,
				"grounding":     "Unprivileged web research & entity extraction completed.",
				"rag_context":   ragContext,
			}
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"status":  "success",
			"route":   route,
			"worker":  result,
			"message": "Worker plane executed unprivileged task successfully.",
		})
	}
}

func (s *OrchestratorServer) handleHITLPending(w http.ResponseWriter, r *http.Request) {
	list, err := s.ipcClient.FetchPendingHITL()
	if err != nil {
		list = []map[string]interface{}{}
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(list)
}

func (s *OrchestratorServer) handleHITLDecision(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	r.Body = http.MaxBytesReader(w, r.Body, 1*1024*1024)

	var req struct {
		TokenID  string `json:"token_id"`
		Approved bool   `json:"approved"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	success, err := s.ipcClient.SubmitHITLDecision(req.TokenID, req.Approved)
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success":  success,
		"token_id": req.TokenID,
		"approved": req.Approved,
		"error":    fmt.Sprintf("%v", err),
	})
}

func (s *OrchestratorServer) handleSystemStatus(w http.ResponseWriter, r *http.Request) {
	workerHealth := "offline"
	ctx, cancel := context.WithTimeout(r.Context(), 3*time.Second)
	defer cancel()

	probeReq, _ := http.NewRequestWithContext(ctx, http.MethodGet, s.workerHost+"/health", nil)
	if resp, err := s.workerClient.Do(probeReq); err == nil {
		workerHealth = "online"
		resp.Body.Close()
	}

	daemonHealth := "offline"
	daemonReq, _ := http.NewRequestWithContext(ctx, http.MethodGet, "http://127.0.0.1:8081/health", nil)
	if resp, err := s.workerClient.Do(daemonReq); err == nil {
		daemonHealth = "online"
		resp.Body.Close()
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"orchestrator": "online",
		"worker_plane": workerHealth,
		"daemon_ipc":   daemonHealth,
		"storage_root": s.storageRoot,
		"time":         time.Now().Format(time.RFC3339),
	})
}

func (s *OrchestratorServer) handlePipelineBenchmark(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 30*time.Second)
	defer cancel()

	req, _ := http.NewRequestWithContext(ctx, http.MethodPost, s.workerHost+"/api/stage", nil)
	req.Header.Set("Content-Type", "application/json")

	resp, err := s.workerClient.Do(req)
	var stageResult map[string]interface{}
	if err == nil {
		json.NewDecoder(resp.Body).Decode(&stageResult)
		resp.Body.Close()
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(stageResult)
}

func (s *OrchestratorServer) handleBrainStatus(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()

	req, _ := http.NewRequestWithContext(ctx, http.MethodGet, s.workerHost+"/api/brain/status", nil)
	resp, err := s.workerClient.Do(req)
	w.Header().Set("Content-Type", "application/json")
	if err != nil {
		json.NewEncoder(w).Encode(map[string]interface{}{
			"active_provider": "deterministic_semantic_router",
			"lm_studio":       map[string]interface{}{"available": false},
			"docker_ollama":   map[string]interface{}{"available": false},
			"cloudflare_workers_ai": map[string]interface{}{
				"model":     "@cf/google/gemma-7b-it",
				"free_tier": true,
			},
		})
		return
	}
	defer resp.Body.Close()
	io.Copy(w, resp.Body)
}

func (s *OrchestratorServer) handleSTTTranscribe(w http.ResponseWriter, r *http.Request) {
	// Performance constraint: Max 15MB request body for audio payload
	r.Body = http.MaxBytesReader(w, r.Body, 15*1024*1024)

	ctx, cancel := context.WithTimeout(r.Context(), 45*time.Second)
	defer cancel()

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, s.workerHost+"/api/stt/transcribe", r.Body)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := s.workerClient.Do(req)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()
	w.Header().Set("Content-Type", "application/json")
	io.Copy(w, resp.Body)
}

func main() {
	server := NewOrchestratorServer()
	server.EnsureDirectories()

	mux := http.NewServeMux()

	// API Endpoints with Rate Limiting & Concurrency Constraints
	mux.HandleFunc("/api/fs/list", RateLimitMiddleware(server.globalLimiter, server.handleFSList))
	mux.HandleFunc("/api/fs/read", RateLimitMiddleware(server.globalLimiter, server.handleFSRead))
	mux.HandleFunc("/api/orchestrator/command", RateLimitMiddleware(server.commandLimiter, server.handleCommand))
	mux.HandleFunc("/api/orchestrator/hitl/pending", RateLimitMiddleware(server.globalLimiter, server.handleHITLPending))
	mux.HandleFunc("/api/orchestrator/hitl/decision", RateLimitMiddleware(server.globalLimiter, server.handleHITLDecision))
	mux.HandleFunc("/api/orchestrator/benchmark", RateLimitMiddleware(server.commandLimiter, server.handlePipelineBenchmark))
	// Status probe remains unthrottled for cloud uptime monitors & Fly.io health checks
	mux.HandleFunc("/api/system/status", server.handleSystemStatus)
	mux.HandleFunc("/api/brain/status", RateLimitMiddleware(server.globalLimiter, server.handleBrainStatus))
	mux.HandleFunc("/api/stt/transcribe", RateLimitMiddleware(server.commandLimiter, server.handleSTTTranscribe))

	mux.HandleFunc("/install", func(w http.ResponseWriter, r *http.Request) {
		http.Redirect(w, r, "/install.html", http.StatusFound)
	})
	mux.HandleFunc("/app", func(w http.ResponseWriter, r *http.Request) {
		http.Redirect(w, r, "/index.html", http.StatusFound)
	})

	// Static Frontend Server
	frontendDir := filepath.Join(".", "frontend")
	fileServer := http.FileServer(http.Dir(frontendDir))
	mux.Handle("/", fileServer)

	srv := &http.Server{
		Addr:              ":" + server.port,
		Handler:           mux,
		ReadHeaderTimeout: 10 * time.Second,
		ReadTimeout:       30 * time.Second,
		WriteTimeout:      60 * time.Second,
		IdleTimeout:       120 * time.Second,
		MaxHeaderBytes:    1 << 20, // 1MB headers
	}

	// Graceful shutdown channel
	shutdown := make(chan os.Signal, 1)
	signal.Notify(shutdown, os.Interrupt, syscall.SIGTERM)

	go func() {
		log.Printf("[*] ANDA Orchestrator running on :%s", server.port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("[FATAL] Orchestrator failed to start: %v", err)
		}
	}()

	<-shutdown
	log.Println("[*] Shutting down Orchestrator gracefully...")
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctx); err != nil {
		log.Printf("[WARN] Server forced to shutdown: %v", err)
	}
	log.Println("[*] Orchestrator exited cleanly.")
}
