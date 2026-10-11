package main

import (
	"fmt"
	"regexp"
	"strings"
)

// IntentDestination identifies which plane an intent targets
type IntentDestination string

const (
	DestWorker   IntentDestination = "WORKER_PLANE"
	DestDaemon   IntentDestination = "ELEVATED_DAEMON"
	DestMemory   IntentDestination = "SHARED_MEMORY"
	DestSecurity IntentDestination = "SECURITY_BLOCKED"
)

// IntentRoute holds routing metadata
type IntentRoute struct {
	Destination IntentDestination `json:"destination"`
	Action      string            `json:"action"`
	Summary     string            `json:"summary"`
	IsPrivileged bool             `json:"is_privileged"`
	Confidence  float64           `json:"confidence"`
}

// PromptInjectionDetector checks for adversarial prompt hijacking
type PromptInjectionDetector struct {
	patterns []*regexp.Regexp
}

func NewPromptInjectionDetector() *PromptInjectionDetector {
	raws := []string{
		`(?i)ignore\s+(all\s+)?(previous|prior)\s+(instructions|prompts|directives)`,
		`(?i)\[system\]`,
		`(?i)<\|im_start\|>\s*system`,
		`(?i)powershell(\.exe)?\s+(-(enc|encodedcommand|e|w\s+hidden)|-nop)`,
		`(?i)cmd(\.exe)?\s+(/c|/k)\s+`,
		`(?i)\b(rmdir|rd)\s+/[sq]`,
		`(?i)\bformat\s+[a-z]:`,
		`(?i)\bdel(\.exe)?\s+/[fqas]`,
		`(?i)\b(curl|wget)\b.*\|\s*(sh|bash|powershell|iex)`,
		`(?i)\bchmod\s+\+x\b`,
	}
	var compiled []*regexp.Regexp
	for _, p := range raws {
		compiled = append(compiled, regexp.MustCompile(p))
	}
	return &PromptInjectionDetector{patterns: compiled}
}

func (pid *PromptInjectionDetector) Scan(text string) (bool, string) {
	for _, reg := range pid.patterns {
		if reg.MatchString(text) {
			return true, fmt.Sprintf("Triggered safety heuristic: %s", reg.String())
		}
	}
	return false, ""
}

// Router evaluates prompt semantics and chooses destination plane
type Router struct {
	detector *PromptInjectionDetector
}

func NewRouter() *Router {
	return &Router{
		detector: NewPromptInjectionDetector(),
	}
}

func (r *Router) RouteIntent(prompt string) (IntentRoute, error) {
	// 1. Pre-execution security hook for indirect prompt injection
	if blocked, reason := r.detector.Scan(prompt); blocked {
		return IntentRoute{
			Destination:  DestSecurity,
			Action:       "blocked_injection",
			Summary:      reason,
			IsPrivileged: false,
			Confidence:   1.0,
		}, fmt.Errorf("pre-execution security hook blocked prompt: %s", reason)
	}

	lower := strings.ToLower(prompt)

	// 2. Elevated Daemon routing (Administrative tasks)
	if strings.Contains(lower, "flash") && (strings.Contains(lower, "usb") || strings.Contains(lower, "drive")) {
		return IntentRoute{
			Destination:  DestDaemon,
			Action:       "flash_usb",
			Summary:      "Elevated action: flash USB device requiring HITL confirmation",
			IsPrivileged: true,
			Confidence:   0.98,
		}, nil
	}
	if strings.Contains(lower, "upgrade") || strings.Contains(lower, "os update") || strings.Contains(lower, "firmware") {
		return IntentRoute{
			Destination:  DestDaemon,
			Action:       "os_update",
			Summary:      "Elevated action: OS or system daemon update",
			IsPrivileged: true,
			Confidence:   0.95,
		}, nil
	}
	if strings.Contains(lower, "format") && strings.Contains(lower, "drive") {
		return IntentRoute{
			Destination:  DestDaemon,
			Action:       "format_drive",
			Summary:      "Elevated action: format storage partition",
			IsPrivileged: true,
			Confidence:   0.99,
		}, nil
	}
	if strings.Contains(lower, "isolate") || strings.Contains(lower, "quarantine") {
		return IntentRoute{
			Destination:  DestDaemon,
			Action:       "quarantine_isolate",
			Summary:      "Elevated administrative lock on quarantined malware",
			IsPrivileged: true,
			Confidence:   0.92,
		}, nil
	}

	// 3. Shared Memory / RAG search queries
	if strings.Contains(lower, "recall") || strings.Contains(lower, "search memory") || strings.Contains(lower, "find in docs") {
		return IntentRoute{
			Destination:  DestMemory,
			Action:       "query_rag",
			Summary:      "Semantic query against shared vector memory",
			IsPrivileged: false,
			Confidence:   0.90,
		}, nil
	}

	// 4. Unprivileged Worker Plane (Research, file parsing, Excel synthesis, staging)
	if strings.Contains(lower, "extract") || strings.Contains(lower, "excel") || strings.Contains(lower, "spreadsheet") {
		return IntentRoute{
			Destination:  DestWorker,
			Action:       "extract_excel",
			Summary:      "Worker task: synthesize extracted multimodal JSON to Excel",
			IsPrivileged: false,
			Confidence:   0.96,
		}, nil
	}
	if strings.Contains(lower, "stage") || strings.Contains(lower, "organize") || strings.Contains(lower, "sort files") {
		return IntentRoute{
			Destination:  DestWorker,
			Action:       "stage_files",
			Summary:      "Worker task: categorize incoming ingest files into staging",
			IsPrivileged: false,
			Confidence:   0.94,
		}, nil
	}

	// Default to research / worker plane
	return IntentRoute{
		Destination:  DestWorker,
		Action:       "web_research",
		Summary:      "Unprivileged research and text grounding",
		IsPrivileged: false,
		Confidence:   0.85,
	}, nil
}
