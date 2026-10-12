package main

import (
	"fmt"
	"net/url"
	"regexp"
	"strings"
)

// IntentDestination identifies which plane an intent targets
type IntentDestination string

const (
	DestWorker        IntentDestination = "WORKER_PLANE"
	DestDaemon        IntentDestination = "ELEVATED_DAEMON"
	DestMemory        IntentDestination = "SHARED_MEMORY"
	DestSecurity      IntentDestination = "SECURITY_BLOCKED"
	DestBrowser       IntentDestination = "BROWSER_NAVIGATE"
	DestWebSearch     IntentDestination = "WEB_SEARCH"
	DestSystemSetting IntentDestination = "SYSTEM_SETTING"
)

// IntentRoute holds routing metadata
type IntentRoute struct {
	Destination  IntentDestination `json:"destination"`
	Action       string            `json:"action"`
	Summary      string            `json:"summary"`
	IsPrivileged bool              `json:"is_privileged"`
	Confidence   float64           `json:"confidence"`
	TargetURL    string            `json:"target_url,omitempty"`
	SystemURI    string            `json:"system_uri,omitempty"`
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

	// 4. System Settings (Windows native settings URIs and tools)
	if strings.Contains(lower, "setting") || strings.Contains(lower, "sound") || strings.Contains(lower, "volume") ||
		strings.Contains(lower, "display") || strings.Contains(lower, "bluetooth") || strings.Contains(lower, "wifi") ||
		strings.Contains(lower, "task manager") || strings.Contains(lower, "taskmgr") || strings.Contains(lower, "calculator") ||
		strings.Contains(lower, "control panel") {
		uri, desc := ResolveSystemSetting(prompt)
		return IntentRoute{
			Destination:  DestSystemSetting,
			Action:       "open_setting",
			Summary:      fmt.Sprintf("Open Windows %s (%s)", desc, uri),
			IsPrivileged: false,
			Confidence:   0.98,
			SystemURI:    uri,
		}, nil
	}

	// 5. Internet Web Search
	if strings.Contains(lower, "on the internet") || strings.HasPrefix(lower, "search ") || strings.HasPrefix(lower, "google ") ||
		strings.HasPrefix(lower, "look up ") || strings.Contains(lower, "search for ") {
		searchURL, query := ResolveWebSearch(prompt)
		return IntentRoute{
			Destination:  DestWebSearch,
			Action:       "web_search",
			Summary:      fmt.Sprintf("Search the internet for '%s'", query),
			IsPrivileged: false,
			Confidence:   0.96,
			TargetURL:    searchURL,
		}, nil
	}

	// 6. Browser & Website Navigation (with holistic link autocomplete)
	if strings.HasPrefix(lower, "open ") || strings.HasPrefix(lower, "go to ") || strings.HasPrefix(lower, "visit ") ||
		strings.HasPrefix(lower, "browse ") || strings.HasPrefix(lower, "launch ") || strings.Contains(lower, ".com") ||
		strings.Contains(lower, ".org") || strings.Contains(lower, ".io") || strings.Contains(lower, ".net") ||
		strings.Contains(lower, "youtube") || strings.Contains(lower, "browser") {
		targetURL := ResolveBrowserTarget(prompt)
		return IntentRoute{
			Destination:  DestBrowser,
			Action:       "open_browser",
			Summary:      fmt.Sprintf("Open %s in default browser", targetURL),
			IsPrivileged: false,
			Confidence:   0.95,
			TargetURL:    targetURL,
		}, nil
	}

	// 7. Unprivileged Worker Plane (File parsing, Excel synthesis, staging)
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

// ResolveBrowserTarget autocompletes domain names and known services to fully qualified HTTPS URLs
func ResolveBrowserTarget(prompt string) string {
	lower := strings.ToLower(strings.TrimSpace(prompt))

	prefixes := []string{
		"open a browser and go to ",
		"open a browser and visit ",
		"open browser and go to ",
		"open browser to ",
		"open browser and search ",
		"open the browser and visit ",
		"open a browser",
		"open the browser",
		"open browser",
		"navigate to ",
		"go to ",
		"visit ",
		"browse to ",
		"browse ",
		"launch ",
		"open ",
	}
	target := lower
	for _, p := range prefixes {
		if strings.HasPrefix(target, p) {
			target = strings.TrimSpace(target[len(p):])
			break
		}
	}

	if target == "" {
		return "https://www.google.com"
	}
	target = strings.TrimRight(target, ".!?,; ")

	knownSites := map[string]string{
		"youtube":   "https://www.youtube.com",
		"google":    "https://www.google.com",
		"github":    "https://github.com",
		"reddit":    "https://www.reddit.com",
		"twitter":   "https://x.com",
		"x":         "https://x.com",
		"dribbble":  "https://dribbble.com",
		"wikipedia": "https://www.wikipedia.org",
		"gmail":     "https://mail.google.com",
		"netflix":   "https://www.netflix.com",
		"spotify":   "https://open.spotify.com",
		"chatgpt":   "https://chatgpt.com",
		"amazon":    "https://www.amazon.com",
		"linkedin":  "https://www.linkedin.com",
		"twitch":    "https://www.twitch.tv",
		"instagram": "https://www.instagram.com",
	}
	if urlVal, exists := knownSites[target]; exists {
		return urlVal
	}

	if strings.HasPrefix(target, "http://") || strings.HasPrefix(target, "https://") {
		return target
	}

	if strings.Contains(target, ".") && !strings.Contains(target, " ") {
		return "https://" + target
	}

	if !strings.Contains(target, " ") {
		return "https://www." + target + ".com"
	}

	return "https://www.google.com/search?q=" + url.QueryEscape(target)
}

// ResolveSystemSetting maps user intent to Windows URI schemes or native app launchers
func ResolveSystemSetting(prompt string) (uri string, desc string) {
	lower := strings.ToLower(prompt)
	switch {
	case strings.Contains(lower, "sound") || strings.Contains(lower, "volume") || strings.Contains(lower, "audio"):
		return "ms-settings:sound", "Sound & Audio Settings"
	case strings.Contains(lower, "display") || strings.Contains(lower, "screen") || strings.Contains(lower, "resolution") || strings.Contains(lower, "brightness"):
		return "ms-settings:display", "Display Settings"
	case strings.Contains(lower, "wifi") || strings.Contains(lower, "wi-fi") || strings.Contains(lower, "network") || strings.Contains(lower, "internet"):
		return "ms-settings:network-wifi", "Network & Wi-Fi Settings"
	case strings.Contains(lower, "bluetooth") || strings.Contains(lower, "devices"):
		return "ms-settings:bluetooth", "Bluetooth & Devices Settings"
	case strings.Contains(lower, "update") || strings.Contains(lower, "windows update"):
		return "ms-settings:windowsupdate", "Windows Update Settings"
	case strings.Contains(lower, "battery") || strings.Contains(lower, "power") || strings.Contains(lower, "sleep"):
		return "ms-settings:powersleep", "Power & Battery Settings"
	case strings.Contains(lower, "storage") || strings.Contains(lower, "disk space"):
		return "ms-settings:storagesense", "Storage Settings"
	case strings.Contains(lower, "task manager") || strings.Contains(lower, "taskmgr"):
		return "taskmgr", "Task Manager"
	case strings.Contains(lower, "calculator") || strings.Contains(lower, "calc"):
		return "calc", "Calculator"
	case strings.Contains(lower, "control panel"):
		return "control", "Control Panel"
	default:
		return "ms-settings:", "Windows Settings"
	}
}

// ResolveWebSearch parses internet search queries and generates web search URLs
func ResolveWebSearch(prompt string) (searchURL string, query string) {
	lower := strings.ToLower(strings.TrimSpace(prompt))
	prefixes := []string{
		"search something on the internet for ",
		"search something on the internet about ",
		"search something on the internet",
		"search the internet for ",
		"search the internet about ",
		"search the internet",
		"search on the internet for ",
		"search on the internet",
		"search for ",
		"search about ",
		"search ",
		"google for ",
		"google ",
		"look up ",
		"find on internet ",
		"find ",
	}
	clean := lower
	for _, p := range prefixes {
		if strings.HasPrefix(clean, p) {
			clean = strings.TrimSpace(clean[len(p):])
			break
		}
	}
	clean = strings.TrimSuffix(clean, " on the internet")
	clean = strings.TrimSuffix(clean, " in google")
	clean = strings.TrimSuffix(clean, " on google")
	clean = strings.Trim(clean, ".!?,; ")

	if clean == "" {
		clean = "technology trends"
	}
	return "https://www.google.com/search?q=" + url.QueryEscape(clean), clean
}
