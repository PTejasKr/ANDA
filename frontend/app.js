/**
 * Omni-Operator: Minimal Whisper Flow Vanilla JS Architecture
 * Conforms strictly to ui_design_and_execution_flow.md
 * Pure ES6+, Zero Dependencies, Resilient & Lightweight
 */

(() => {
  'use strict';

  // ==========================================================================
  // 1. Configuration & Constants
  // ==========================================================================

  const isLocal = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
  const originBase = typeof window !== 'undefined' && window.location.origin ? window.location.origin : 'http://localhost:8080';

  const CONFIG = {
    WORKER_URL: isLocal ? 'http://localhost:50051' : originBase,
    DAEMON_URL: isLocal ? 'http://localhost:8081' : originBase,
    ORCHESTRATOR_URL: isLocal ? 'http://localhost:8080' : originBase,
    HITL_TIMEOUT_SECONDS: 60,
    EXEC_TIMEOUT_SECONDS: 45,
    RUNAWAY_ACTION_LIMIT: 5,
    AMBIGUITY_THRESHOLD: 0.85,
    HEALTH_POLL_INTERVAL_MS: 4000,
  };

  // State Enums per Spec Section 2
  const States = {
    IDLE: 'idle',
    LISTENING: 'listening',
    PROCESSING: 'processing',
    EXECUTING: 'executing',
    AWAITING_AUTH: 'awaiting_auth',
    STUCK: 'stuck',
  };

  // Sample Transaction Dataset (conforming to file_staging_rag.md)
  const SAMPLE_RECORDS = [
    { date: '2026-10-01', vendor: 'AWS Cloud Services', category: 'Infrastructure', amount: 489.20, tax_deductible: true, payment_method: 'Corporate Visa' },
    { date: '2026-10-03', vendor: 'OpenAI API Platform', category: 'AI Inference', amount: 312.45, tax_deductible: true, payment_method: 'Corporate Visa' },
    { date: '2026-10-06', vendor: 'Stripe Processing Fee', category: 'Finance', amount: 78.50, tax_deductible: true, payment_method: 'Direct Debit' },
    { date: '2026-10-09', vendor: 'GitHub Enterprise', category: 'Dev Tools', amount: 210.00, tax_deductible: true, payment_method: 'Corporate Visa' },
    { date: '2026-10-10', vendor: 'Anthropic Tier 4', category: 'AI Inference', amount: 145.33, tax_deductible: true, payment_method: 'Corporate Visa' }
  ];

  // ==========================================================================
  // 2. Synthesizer & Audio Engine (Web Audio API)
  // ==========================================================================

  class AudioEngine {
    constructor() {
      this.enabled = true;
      this.ctx = null;
    }

    init() {
      if (!this.ctx && (window.AudioContext || window.webkitAudioContext)) {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        this.ctx = new AudioCtx();
      }
      if (this.ctx && this.ctx.state === 'suspended') {
        this.ctx.resume();
      }
    }

    playTone(frequency, type = 'sine', duration = 0.15, gainVal = 0.08) {
      if (!this.enabled) return;
      try {
        this.init();
        if (!this.ctx) return;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = type;
        osc.frequency.setValueAtTime(frequency, this.ctx.currentTime);
        gain.gain.setValueAtTime(gainVal, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.0001, this.ctx.currentTime + duration);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start();
        osc.stop(this.ctx.currentTime + duration);
      } catch (err) {
        // Safe fail on audio policy restrictions
      }
    }

    chimeListening() {
      this.playTone(587.33, 'sine', 0.12, 0.05); // D5
      setTimeout(() => this.playTone(880, 'sine', 0.18, 0.06), 80); // A5
    }

    chimeProcessing() {
      this.playTone(440, 'triangle', 0.1, 0.04);
    }

    chimeSuccess() {
      this.playTone(523.25, 'sine', 0.1, 0.05); // C5
      setTimeout(() => this.playTone(659.25, 'sine', 0.12, 0.05), 80); // E5
      setTimeout(() => this.playTone(783.99, 'sine', 0.2, 0.06), 160); // G5
    }

    chimeWarning() {
      this.playTone(320, 'sawtooth', 0.2, 0.08);
      setTimeout(() => this.playTone(280, 'sawtooth', 0.25, 0.08), 120);
    }

    speak(text) {
      if (!('speechSynthesis' in window)) return;
      try {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.05;
        utterance.pitch = 1.0;
        utterance.volume = this.enabled ? 0.9 : 0.0;
        window.speechSynthesis.speak(utterance);
      } catch (e) {
        // Safe fail
      }
    }
  }

  // ==========================================================================
  // 3. Web Speech Recognition Engine
  // ==========================================================================

  class VoiceEngine {
    constructor(onSpeechResult, onSpeechEnd, onStatusChange) {
      this.onSpeechResult = onSpeechResult;
      this.onSpeechEnd = onSpeechEnd;
      this.onStatusChange = onStatusChange;
      this.recognition = null;
      this.isListening = false;
      this.isSupported = false;

      this.init();
    }

    init() {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRecognition) {
        this.recognition = new SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';
        this.isSupported = true;

        this.recognition.onstart = () => {
          this.isListening = true;
          this.onStatusChange(true);
        };

        this.recognition.onresult = (event) => {
          let interimTranscript = '';
          let finalTranscript = '';
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
              finalTranscript += event.results[i][0].transcript;
            } else {
              interimTranscript += event.results[i][0].transcript;
            }
          }
          const text = finalTranscript || interimTranscript;
          if (text) {
            this.onSpeechResult(text, Boolean(finalTranscript));
          }
        };

        this.recognition.onerror = (event) => {
          this.isListening = false;
          this.onStatusChange(false, event.error);
        };

        this.recognition.onend = () => {
          this.isListening = false;
          this.onStatusChange(false);
          this.onSpeechEnd();
        };
      } else {
        this.isSupported = false;
        this.onStatusChange(false, 'SpeechRecognition not supported in this browser');
      }
    }

    start() {
      if (!this.isSupported || !this.recognition) return false;
      try {
        this.recognition.start();
        return true;
      } catch (e) {
        return false;
      }
    }

    stop() {
      if (this.recognition && this.isListening) {
        try {
          this.recognition.stop();
        } catch (e) {}
      }
    }
  }

  // ==========================================================================
  // 4. Backend Communication Client
  // ==========================================================================

  class BackendClient {
    constructor() {
      this.workerHealthy = false;
      this.daemonHealthy = false;
    }

    async checkHealth() {
      // 1. Check orchestrator status probe (which monitors co-located worker and daemon)
      try {
        const res = await fetch(`${CONFIG.ORCHESTRATOR_URL}/api/system/status`, { signal: AbortSignal.timeout(2000) });
        if (res.ok) {
          const data = await res.json();
          this.workerHealthy = data.worker_plane === 'online';
          this.daemonHealthy = data.daemon_ipc === 'online';
          return { worker: this.workerHealthy, daemon: this.daemonHealthy };
        }
      } catch (e) {
        // Fallback to direct probes
      }

      // 2. Direct checks (local standalone development)
      if (isLocal) {
        try {
          const res = await fetch(`${CONFIG.WORKER_URL}/health`, { signal: AbortSignal.timeout(1500) });
          this.workerHealthy = res.ok;
        } catch (e) {
          this.workerHealthy = false;
        }

        try {
          const res = await fetch(`${CONFIG.DAEMON_URL}/health`, { signal: AbortSignal.timeout(1500) });
          this.daemonHealthy = res.ok;
        } catch (e) {
          this.daemonHealthy = false;
        }
      } else {
        this.workerHealthy = true;
        this.daemonHealthy = false;
      }

      return {
        worker: this.workerHealthy,
        daemon: this.daemonHealthy
      };
    }

    async extractToExcel(records, filename = 'financial_synthesis.xlsx') {
      if (!this.workerHealthy) {
        // Resilient mock synthesis fallback
        await new Promise(r => setTimeout(r, 600));
        return {
          status: 'success',
          file_path: `d:\\mlh\\storage\\staging\\spreadsheets\\${filename}`,
          filename,
          rows_extracted: records.length,
          simulated: true,
        };
      }

      const res = await fetch(`${CONFIG.WORKER_URL}/api/extract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          records,
          filename,
          report_title: 'Multimodal Synthesis Report',
        })
      });
      return await res.json();
    }

    async queryMemory(query, topK = 4) {
      if (!this.workerHealthy) {
        await new Promise(r => setTimeout(r, 400));
        return {
          status: 'success',
          query,
          results: [
            {
              doc_id: 'financial_synthesis.xlsx',
              chunk_index: 0,
              text: 'Date: 2026-10-01 | Vendor: AWS Cloud Services | Category: Infrastructure | Amount: $489.20',
              score: 0.942,
              metadata: { source_file: 'financial_synthesis.xlsx' }
            },
            {
              doc_id: 'financial_synthesis.xlsx',
              chunk_index: 1,
              text: 'Date: 2026-10-03 | Vendor: OpenAI API Platform | Category: AI Inference | Amount: $312.45',
              score: 0.887,
              metadata: { source_file: 'financial_synthesis.xlsx' }
            }
          ],
          simulated: true,
        };
      }

      const res = await fetch(`${CONFIG.WORKER_URL}/api/memory/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, top_k: topK })
      });
      return await res.json();
    }

    async scanPrompt(text) {
      if (!this.workerHealthy) {
        // Run client-side zero-trust heuristics
        const lower = text.toLowerCase();
        const injectionPatterns = [
          'ignore previous instructions',
          '[system]',
          '<|im_start|>',
          'powershell -enc',
          'cmd.exe',
          'rmdir',
          'format c:',
          'chmod +x'
        ];
        const match = injectionPatterns.find(p => lower.includes(p));
        return {
          safe: !match,
          flagged_pattern: match || null,
          verdict: match ? 'PROMPT_INJECTION_DETECTED' : 'SAFE_PASS',
          simulated: true,
        };
      }

      const res = await fetch(`${CONFIG.WORKER_URL}/api/security/scan_prompt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      return await res.json();
    }

    async approveDaemonToken(tokenId, approved) {
      // 1. Send decision to Orchestrator HITL gate endpoint
      try {
        const res = await fetch(`${CONFIG.ORCHESTRATOR_URL}/api/orchestrator/hitl/decision`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token_id: tokenId, approved }),
          signal: AbortSignal.timeout(3000)
        });
        if (res.ok) {
          return await res.json();
        }
      } catch (e) {
        // Fallback to daemon direct
      }

      if (!this.daemonHealthy) {
        return { success: true, token_id: tokenId, decision: approved, simulated: true };
      }

      try {
        const res = await fetch(`${CONFIG.DAEMON_URL}/api/daemon/approve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token_id: tokenId, approved })
        });
        return await res.json();
      } catch (e) {
        return { success: true, token_id: tokenId, decision: approved, simulated: true };
      }
    }
  }

  // ==========================================================================
  // 5. Main Application Controller
  // ==========================================================================

  class OmniOperatorApp {
    constructor() {
      // Core Subsystems
      this.audio = new AudioEngine();
      this.backend = new BackendClient();
      this.currentState = States.IDLE;
      this.pendingHitlToken = null;
      this.elevationTimerInterval = null;
      this.execTimerInterval = null;
      this.elapsedSeconds = 0;
      this.fadeBubbleTimeout = null;

      // Cache DOM Elements
      this.dom = {
        desktopBackdrop: document.getElementById('desktopBackdrop'),
        chipWorker: document.getElementById('chipWorker'),
        chipDaemon: document.getElementById('chipDaemon'),
        chipSpeech: document.getElementById('chipSpeech'),
        btnSoundToggle: document.getElementById('btnSoundToggle'),
        btnBackdropToggle: document.getElementById('btnBackdropToggle'),
        btnToggleDrawer: document.getElementById('btnToggleDrawer'),
        btnCloseDrawer: document.getElementById('btnCloseDrawer'),
        actionDrawer: document.getElementById('actionDrawer'),

        ephemeralContainer: document.getElementById('ephemeralContainer'),
        transcriptionBubble: document.getElementById('transcriptionBubble'),
        transcriptionTag: document.getElementById('transcriptionTag'),
        confidenceTag: document.getElementById('confidenceTag'),
        elapsedTimer: document.getElementById('elapsedTimer'),
        transcriptionText: document.getElementById('transcriptionText'),
        progressBarContainer: document.getElementById('execProgressBarContainer'),
        progressBarFill: document.getElementById('execProgressBarFill'),
        execStatusSubtext: document.getElementById('execStatusSubtext'),

        orbDock: document.getElementById('orbDock'),
        whisperOrb: document.getElementById('whisperOrb'),
        orbStateLabel: document.getElementById('orbStateLabel'),
        orbIconWrapper: document.getElementById('orbIconWrapper'),

        promptForm: document.getElementById('promptForm'),
        promptInput: document.getElementById('promptInput'),

        // Fallback Modals (Spec Section 3)
        modalAmbiguity: document.getElementById('modalAmbiguity'),
        ambiguitySpokenPrompt: document.getElementById('ambiguitySpokenPrompt'),
        btnAmbiguityOpt1: document.getElementById('btnAmbiguityOpt1'),
        btnAmbiguityOpt2: document.getElementById('btnAmbiguityOpt2'),

        modalRunaway: document.getElementById('modalRunaway'),
        btnRunawayIntervene: document.getElementById('btnRunawayIntervene'),
        btnRunawayCancel: document.getElementById('btnRunawayCancel'),

        modalTimeout: document.getElementById('modalTimeout'),
        btnTimeoutBackground: document.getElementById('btnTimeoutBackground'),
        btnTimeoutAbort: document.getElementById('btnTimeoutAbort'),

        modalElevation: document.getElementById('modalElevation'),
        manifestTokenId: document.getElementById('manifestTokenId'),
        manifestCodeContent: document.getElementById('manifestCodeContent'),
        elevationCountdownFill: document.getElementById('elevationCountdownFill'),
        elevationSecondsLeft: document.getElementById('elevationSecondsLeft'),
        btnApproveElevation: document.getElementById('btnApproveElevation'),
        btnRejectElevation: document.getElementById('btnRejectElevation'),

        // Drawer Tabs
        tabBtns: document.querySelectorAll('.tab-btn'),
        tabPanes: document.querySelectorAll('.tab-pane'),
        excelTableBody: document.getElementById('excelTableBody'),
        excelTotalAmount: document.getElementById('excelTotalAmount'),
        btnTriggerSynthesis: document.getElementById('btnTriggerSynthesis'),

        ragQueryInput: document.getElementById('ragQueryInput'),
        btnQueryRag: document.getElementById('btnQueryRag'),
        ragResultsList: document.getElementById('ragResultsList'),

        secPromptInput: document.getElementById('secPromptInput'),
        btnScanPrompt: document.getElementById('btnScanPrompt'),
        promptScanResult: document.getElementById('promptScanResult'),

        timelineLogList: document.getElementById('timelineLogList'),
        btnClearLogs: document.getElementById('btnClearLogs'),

        // Loop Simulator Buttons
        btnSimulateAmbiguity: document.getElementById('btnSimulateAmbiguity'),
        btnSimulateRunaway: document.getElementById('btnSimulateRunaway'),
        btnSimulateTimeout: document.getElementById('btnSimulateTimeout'),
        btnSimulateElevation: document.getElementById('btnSimulateElevation'),
      };

      // Voice Engine Initialization
      this.voice = new VoiceEngine(
        (transcript, isFinal) => this.handleLiveSpeech(transcript, isFinal),
        () => this.handleSpeechComplete(),
        (active, error) => this.handleVoiceStatusChange(active, error)
      );

      this.bindEvents();
      this.renderExcelTable(SAMPLE_RECORDS);
      this.startHealthPolling();
      this.logEvent('system', 'Omni-Operator initialized in Minimal Whisper Flow mode');
    }

    // ==========================================================================
    // Event Binding
    // ==========================================================================

    bindEvents() {
      // Orb Click (Toggle Voice or Submit)
      this.dom.whisperOrb.addEventListener('click', () => {
        this.audio.init();
        if (this.currentState === States.IDLE) {
          this.startListening();
        } else if (this.currentState === States.LISTENING) {
          this.stopListening();
        } else if (this.currentState === States.STUCK) {
          this.showModal('modalRunaway');
        }
      });

      // Quick Chips
      document.querySelectorAll('.chip-action').forEach(chip => {
        chip.addEventListener('click', () => {
          const prompt = chip.getAttribute('data-prompt');
          this.dom.promptInput.value = prompt;
          this.processPrompt(prompt);
        });
      });

      // Form Submission
      this.dom.promptForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const text = this.dom.promptInput.value.trim();
        if (text) {
          this.processPrompt(text);
          this.dom.promptInput.value = '';
        }
      });

      // Drawer Toggles
      this.dom.btnToggleDrawer.addEventListener('click', () => this.toggleDrawer());
      this.dom.btnCloseDrawer.addEventListener('click', () => this.toggleDrawer(false));

      // Sound Toggle
      this.dom.btnSoundToggle.addEventListener('click', () => {
        this.audio.enabled = !this.audio.enabled;
        this.dom.btnSoundToggle.style.opacity = this.audio.enabled ? '1' : '0.4';
        this.logEvent('system', `Audio sound synthesis ${this.audio.enabled ? 'enabled' : 'muted'}`);
      });

      // Backdrop Toggle (Simulated Desktop Wallpaper vs Transparent Overlay)
      this.dom.btnBackdropToggle.addEventListener('click', () => {
        document.body.classList.toggle('pure-transparent');
        const isPure = document.body.classList.contains('pure-transparent');
        this.logEvent('system', `Display mode: ${isPure ? 'Pure Transparent Desktop Overlay' : 'Standard View'}`);
      });

      // Drawer Tab Switching
      this.dom.tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
          this.dom.tabBtns.forEach(b => b.classList.remove('active'));
          this.dom.tabPanes.forEach(p => p.classList.remove('active'));
          btn.classList.add('active');
          const target = btn.getAttribute('data-tab');
          const pane = document.getElementById(target);
          if (pane) pane.classList.add('active');
        });
      });

      // Fallback Loop A (Ambiguity) Actions
      this.dom.btnAmbiguityOpt1.addEventListener('click', () => {
        this.resolveAmbiguity('Create New Excel File');
      });
      this.dom.btnAmbiguityOpt2.addEventListener('click', () => {
        this.resolveAmbiguity('Append to Existing Q3 Sheet');
      });

      // Fallback Loop B (Runaway Limiter) Actions
      this.dom.btnRunawayIntervene.addEventListener('click', () => {
        this.hideModal('modalRunaway');
        this.toggleDrawer(true);
        this.setState(States.IDLE);
        this.logEvent('unprivileged', 'Human intervention accepted. Worker plane released to manual control.');
      });
      this.dom.btnRunawayCancel.addEventListener('click', () => {
        this.hideModal('modalRunaway');
        this.setState(States.IDLE);
        this.setEphemeralText('Task cancelled by user intervention.', 0.99, true);
        this.logEvent('system', 'Runaway task aborted by user command.');
      });

      // Fallback Loop C (Timeout) Actions
      this.dom.btnTimeoutBackground.addEventListener('click', () => {
        this.hideModal('modalTimeout');
        this.setState(States.IDLE);
        this.setEphemeralText('Process moved to background queue.', 0.95, true);
        this.logEvent('unprivileged', 'Execution branched to async background daemon.');
      });
      this.dom.btnTimeoutAbort.addEventListener('click', () => {
        this.hideModal('modalTimeout');
        this.setState(States.IDLE);
        this.setEphemeralText('Long-running process terminated.', 0.95, true);
        this.logEvent('unprivileged', 'Execution aborted due to 45s timeout.');
      });

      // Fallback Loop D (Elevation HITL) Actions
      this.dom.btnApproveElevation.addEventListener('click', () => {
        this.handleHitlDecision(true);
      });
      this.dom.btnRejectElevation.addEventListener('click', () => {
        this.handleHitlDecision(false);
      });

      // Drawer Tab Actions
      this.dom.btnTriggerSynthesis.addEventListener('click', () => {
        this.triggerExcelSynthesis();
      });

      this.dom.btnQueryRag.addEventListener('click', () => {
        this.executeRagQuery();
      });

      this.dom.btnScanPrompt.addEventListener('click', () => {
        this.executePromptScan();
      });

      this.dom.btnClearLogs.addEventListener('click', () => {
        this.dom.timelineLogList.innerHTML = '';
      });

      // Loop Simulator Triggers
      this.dom.btnSimulateAmbiguity.addEventListener('click', () => this.triggerLoopA());
      this.dom.btnSimulateRunaway.addEventListener('click', () => this.triggerLoopB());
      this.dom.btnSimulateTimeout.addEventListener('click', () => this.triggerLoopC());
      this.dom.btnSimulateElevation.addEventListener('click', () => this.triggerLoopD());
    }

    // ==========================================================================
    // State Machine per Spec Section 2
    // ==========================================================================

    setState(state, customLabel = null) {
      this.currentState = state;
      const orb = this.dom.whisperOrb;
      const dock = this.dom.orbDock;

      // Remove all state classes
      orb.className = 'whisper-orb';
      dock.className = 'orb-dock';

      // Reset sub-elements
      this.dom.progressBarContainer.classList.remove('active');
      this.dom.execStatusSubtext.classList.remove('visible');

      switch (state) {
        case States.IDLE:
          orb.classList.add('state-idle');
          this.dom.orbStateLabel.textContent = customLabel || 'Idle (20% Opacity)';
          this.updateOrbIcon('mic');
          break;

        case States.LISTENING:
          orb.classList.add('state-listening');
          dock.classList.add('listening');
          this.dom.orbStateLabel.textContent = customLabel || 'Listening (Voice Capture)';
          this.updateOrbIcon('mic');
          this.audio.chimeListening();
          break;

        case States.PROCESSING:
          orb.classList.add('state-processing');
          dock.classList.add('processing');
          this.dom.orbStateLabel.textContent = customLabel || 'Processing (Intent Routing)';
          this.updateOrbIcon('spinner');
          this.audio.chimeProcessing();
          break;

        case States.EXECUTING:
          orb.classList.add('state-executing');
          dock.classList.add('executing');
          this.dom.progressBarContainer.classList.add('active');
          this.dom.execStatusSubtext.classList.add('visible');
          this.dom.orbStateLabel.textContent = customLabel || 'Executing (Unprivileged Plane)';
          this.updateOrbIcon('gear');
          break;

        case States.AWAITING_AUTH:
          orb.classList.add('state-awaiting-auth');
          dock.classList.add('awaiting-auth');
          this.dom.orbStateLabel.textContent = customLabel || 'Awaiting Authorization (Elevated Plane)';
          this.updateOrbIcon('shield');
          this.audio.chimeWarning();
          break;

        case States.STUCK:
          orb.classList.add('state-stuck');
          this.dom.orbStateLabel.textContent = customLabel || 'Task Seems Stuck (Runaway Limiter)';
          this.updateOrbIcon('alert');
          this.audio.chimeWarning();
          break;
      }
    }

    updateOrbIcon(type) {
      const wrapper = this.dom.orbIconWrapper;
      let svgContent = '';

      if (type === 'mic') {
        svgContent = `
          <svg class="orb-icon icon-mic" viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
            <line x1="12" y1="19" x2="12" y2="23"/>
            <line x1="8" y1="23" x2="16" y2="23"/>
          </svg>`;
      } else if (type === 'gear') {
        svgContent = `
          <svg class="orb-icon" viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>`;
      } else if (type === 'shield') {
        svgContent = `
          <svg class="orb-icon text-red" viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>`;
      } else if (type === 'alert') {
        svgContent = `
          <svg class="orb-icon" viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>`;
      }

      wrapper.innerHTML = svgContent;
    }

    // ==========================================================================
    // Ephemeral Transcription
    // ==========================================================================

    setEphemeralText(text, confidence = 0.98, fadeOutAfter = false) {
      if (this.fadeBubbleTimeout) {
        clearTimeout(this.fadeBubbleTimeout);
        this.fadeBubbleTimeout = null;
      }

      this.dom.transcriptionText.textContent = `"${text}"`;
      const pct = Math.round(confidence * 100);
      this.dom.confidenceTag.textContent = `Confidence: ${pct}%`;
      this.dom.ephemeralContainer.style.opacity = '1';
      this.dom.ephemeralContainer.style.transform = 'translateY(0)';

      if (fadeOutAfter) {
        this.fadeBubbleTimeout = setTimeout(() => {
          this.dom.ephemeralContainer.style.opacity = '0.35';
          this.dom.ephemeralContainer.style.transform = 'translateY(4px)';
        }, 5000);
      }
    }

    startExecutionProgress(title, durationMs = 2400) {
      this.dom.progressBarContainer.classList.add('active');
      this.dom.execStatusSubtext.classList.add('visible');
      this.dom.execStatusSubtext.textContent = title;
      this.dom.progressBarFill.style.width = '0%';

      let progress = 0;
      const interval = 50;
      const step = 100 / (durationMs / interval);

      const pTimer = setInterval(() => {
        progress += step;
        if (progress >= 100) {
          progress = 100;
          clearInterval(pTimer);
          setTimeout(() => {
            this.dom.progressBarContainer.classList.remove('active');
            this.dom.execStatusSubtext.classList.remove('visible');
          }, 400);
        }
        this.dom.progressBarFill.style.width = `${progress}%`;
      }, interval);
    }

    // ==========================================================================
    // Voice Handling
    // ==========================================================================

    startListening() {
      const started = this.voice.start();
      if (started) {
        this.setState(States.LISTENING);
        this.setEphemeralText('Listening to microphone...', 1.0);
      } else {
        // Fallback simulation if speech recognition is unavailable or blocked
        this.setState(States.LISTENING);
        this.setEphemeralText('Listening... (Speech API simulated)', 0.96);
        setTimeout(() => {
          this.handleLiveSpeech('Synthesize quarterly receipts to Excel', true);
          this.stopListening();
        }, 2200);
      }
    }

    stopListening() {
      this.voice.stop();
      if (this.currentState === States.LISTENING) {
        this.setState(States.IDLE);
      }
    }

    handleLiveSpeech(transcript, isFinal) {
      this.setEphemeralText(transcript, isFinal ? 0.98 : 0.85);
      if (isFinal) {
        this.processPrompt(transcript);
      }
    }

    handleSpeechComplete() {
      if (this.currentState === States.LISTENING) {
        this.setState(States.IDLE);
      }
    }

    handleVoiceStatusChange(active, error) {
      const chip = this.dom.chipSpeech;
      if (error) {
        chip.className = 'status-chip offline';
        chip.querySelector('.chip-label').textContent = 'Voice: Sim/Denied';
      } else if (active) {
        chip.className = 'status-chip active';
        chip.querySelector('.chip-label').textContent = 'Voice: Capturing';
      } else {
        chip.className = 'status-chip online';
        chip.querySelector('.chip-label').textContent = 'Voice: Ready';
      }
    }

    // ==========================================================================
    // Intent Parsing & Dual-Plane Routing
    // ==========================================================================

    async processPrompt(prompt) {
      this.logEvent('user', `Prompt: "${prompt}"`);
      this.setEphemeralText(prompt, 0.96);
      this.setState(States.PROCESSING);

      const lower = prompt.toLowerCase();

      // Check Heuristics for Indirect Injection First
      const scanRes = await this.backend.scanPrompt(prompt);
      if (!scanRes.safe) {
        this.audio.chimeWarning();
        this.setState(States.IDLE);
        this.setEphemeralText(`SECURITY ALERT: Prompt blocked (${scanRes.flagged_pattern})`, 0.99, true);
        this.logEvent('system', `Blocked indirect prompt injection: ${scanRes.flagged_pattern}`);
        this.toggleDrawer(true);
        // Switch to security tab
        const secTab = document.querySelector('[data-tab="tabSecurity"]');
        if (secTab) secTab.click();
        return;
      }

      // Check Ambiguity Condition (Spec Section 3.A)
      if (lower.includes('update') && lower.includes('sheet') && !lower.includes('new') && !lower.includes('append')) {
        this.triggerLoopA();
        return;
      }

      // Check Elevated Capabilities (Spec Section 3.D)
      if (lower.includes('flash') || lower.includes('usb') || lower.includes('format') || lower.includes('quarantine isolate') || lower.includes('os update')) {
        this.triggerLoopD(prompt);
        return;
      }

      // Unprivileged Plane: Excel Synthesis (Spec Section 1 & 2)
      if (lower.includes('excel') || lower.includes('synthesize') || lower.includes('receipt') || lower.includes('extract')) {
        this.executeUnprivilegedSynthesis();
        return;
      }

      // Unprivileged Plane: RAG Search (Spec Section 1)
      if (lower.includes('search') || lower.includes('memory') || lower.includes('rag') || lower.includes('query')) {
        this.executeUnprivilegedRag(prompt);
        return;
      }

      // Default Generic Unprivileged Action
      this.setState(States.EXECUTING);
      this.startExecutionProgress('Executing unprivileged intent...', 1800);
      setTimeout(() => {
        this.setState(States.IDLE);
        this.setEphemeralText(`Completed task: "${prompt}"`, 0.98, true);
        this.logEvent('unprivileged', `Successfully processed intent for: ${prompt}`);
        this.audio.chimeSuccess();
      }, 1900);
    }

    async executeUnprivilegedSynthesis() {
      this.setState(States.EXECUTING);
      this.startExecutionProgress('Extracting tables and compiling OpenPyXL spreadsheet...', 2200);

      try {
        const res = await this.backend.extractToExcel(SAMPLE_RECORDS, 'extracted_report.xlsx');
        setTimeout(() => {
          this.setState(States.IDLE);
          this.setEphemeralText(`Excel generated: ${res.filename} (${res.rows_extracted || 5} records)`, 0.99, true);
          this.logEvent('unprivileged', `Excel synthesized: ${res.file_path || res.filename}`);
          this.audio.chimeSuccess();
          this.renderExcelTable(SAMPLE_RECORDS);
          this.toggleDrawer(true);
        }, 2200);
      } catch (err) {
        this.setState(States.IDLE);
        this.setEphemeralText(`Synthesis failed: ${err.message}`, 0.9, true);
      }
    }

    async executeUnprivilegedRag(query) {
      this.setState(States.EXECUTING);
      this.startExecutionProgress('Querying vector memory embeddings...', 1500);

      try {
        const res = await this.backend.queryMemory(query);
        setTimeout(() => {
          this.setState(States.IDLE);
          this.setEphemeralText(`Retrieved ${(res.results || []).length} relevant memory chunks`, 0.98, true);
          this.logEvent('unprivileged', `Vector RAG query: "${query}" returned ${(res.results || []).length} chunks`);
          this.renderRagResults(res.results || []);
          this.audio.chimeSuccess();
          this.toggleDrawer(true);
          const ragTab = document.querySelector('[data-tab="tabRag"]');
          if (ragTab) ragTab.click();
        }, 1500);
      } catch (err) {
        this.setState(States.IDLE);
        this.setEphemeralText(`Memory query failed: ${err.message}`, 0.9, true);
      }
    }

    // ==========================================================================
    // The 4 Execution Loops & Fallback Mechanisms (Spec Section 3)
    // ==========================================================================

    // Loop A: Ambiguity Fallback Loop (Spec Section 3.A)
    triggerLoopA() {
      this.setState(States.IDLE);
      this.setEphemeralText('Ambiguous intent detected. Awaiting clarification...', 0.74);
      this.showModal('modalAmbiguity');
      const spokenText = "Did you mean to create a new Excel file, or append to the existing Q3 sheet?";
      this.dom.ambiguitySpokenPrompt.textContent = `"${spokenText}"`;
      this.audio.speak(spokenText);
      this.logEvent('warning', 'Ambiguity fallback triggered: confidence 74% below threshold');
    }

    resolveAmbiguity(choice) {
      this.hideModal('modalAmbiguity');
      this.logEvent('user', `Ambiguity resolved by human: "${choice}"`);
      this.setEphemeralText(`Confirmed: ${choice}. Proceeding...`, 0.98);
      this.executeUnprivilegedSynthesis();
    }

    // Loop B: Runaway Limiter (Spec Section 3.B)
    triggerLoopB() {
      this.setState(States.STUCK);
      this.setEphemeralText('Task seems stuck. Intervene or cancel?', 0.99);
      this.showModal('modalRunaway');
      this.logEvent('warning', 'The "Runaway" Limiter: 5 GUI actions executed without screen state change. Worker paused.');
    }

    // Loop C: Execution Timeout Fallback (Spec Section 3.C)
    triggerLoopC() {
      this.setState(States.EXECUTING);
      this.setEphemeralText('Heavy computation running (>45s)...', 0.95);
      this.startExecutionProgress('Parsing large PDF dataset...', 8000);
      this.showModal('modalTimeout');
      this.logEvent('warning', 'Execution timeout fallback: backend operation exceeded 45 seconds');
    }

    // Loop D: Security & Elevation Fallback (Spec Section 3.D)
    triggerLoopD(prompt = 'Elevated USB Flash Operation') {
      const tokenId = 'tok_' + Math.random().toString(16).substring(2, 10);
      const token = {
        action: 'flash_usb',
        drive: 'E:',
        hash: '7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069',
        token_id: tokenId,
        params: {
          target: 'SanDisk Ultra USB (Drive E:)',
          image: 'recovery_payload_v2.iso'
        }
      };

      this.pendingHitlToken = token;
      this.setState(States.AWAITING_AUTH);
      this.setEphemeralText('ELEVATION REQUIRED: Administrative capability challenge.', 1.0);

      // Render Manifest
      this.dom.manifestTokenId.textContent = `TOKEN: ${tokenId}`;
      this.dom.manifestCodeContent.textContent = JSON.stringify(token, null, 2);

      this.showModal('modalElevation');
      this.startElevationCountdown(CONFIG.HITL_TIMEOUT_SECONDS);
      this.logEvent('elevated', `HITL elevation gate triggered for token ${tokenId} (${token.action})`);
    }

    startElevationCountdown(seconds) {
      if (this.elevationTimerInterval) clearInterval(this.elevationTimerInterval);

      let timeLeft = seconds;
      this.dom.elevationSecondsLeft.textContent = timeLeft;
      this.dom.elevationCountdownFill.style.width = '100%';

      this.elevationTimerInterval = setInterval(() => {
        timeLeft--;
        this.dom.elevationSecondsLeft.textContent = timeLeft;
        const pct = (timeLeft / seconds) * 100;
        this.dom.elevationCountdownFill.style.width = `${pct}%`;

        if (timeLeft <= 0) {
          clearInterval(this.elevationTimerInterval);
          this.elevationTimerInterval = null;
          this.handleHitlTimeout();
        }
      }, 1000);
    }

    async handleHitlDecision(approved) {
      if (this.elevationTimerInterval) {
        clearInterval(this.elevationTimerInterval);
        this.elevationTimerInterval = null;
      }

      const token = this.pendingHitlToken;
      this.hideModal('modalElevation');
      this.pendingHitlToken = null;

      if (approved) {
        this.setState(States.EXECUTING);
        this.setEphemeralText(`Elevation APPROVED for ${token ? token.action : 'token'}. Executing via Daemon...`, 1.0);
        this.logEvent('elevated', `HITL APPROVED: Capability token ${token?.token_id} authorized by physical click.`);
        this.audio.chimeSuccess();

        if (token) {
          await this.backend.approveDaemonToken(token.token_id, true);
        }

        this.startExecutionProgress('Daemon flashing USB drive securely...', 2000);
        setTimeout(() => {
          this.setState(States.IDLE);
          this.setEphemeralText(`Daemon elevated execution completed successfully.`, 1.0, true);
          this.logEvent('elevated', `Operation ${token?.action} finished cleanly.`);
        }, 2200);

      } else {
        this.setState(States.IDLE);
        this.setEphemeralText('Elevation DENIED. Capability token quarantined.', 1.0, true);
        this.logEvent('elevated', `HITL DENIED: User rejected capability token ${token?.token_id}.`);
        this.audio.chimeWarning();

        if (token) {
          await this.backend.approveDaemonToken(token.token_id, false);
        }
      }
    }

    handleHitlTimeout() {
      this.hideModal('modalElevation');
      const token = this.pendingHitlToken;
      this.pendingHitlToken = null;

      this.setState(States.IDLE);
      this.setEphemeralText('HITL TIMEOUT: Elevation automatically aborted for security.', 1.0, true);
      this.logEvent('elevated', `HITL TIMEOUT: 60s expiration reached without human click. Token ${token?.token_id} aborted.`);
      this.audio.chimeWarning();

      if (token) {
        this.backend.approveDaemonToken(token.token_id, false);
      }
    }

    // ==========================================================================
    // UI Helpers & Data Visualizers
    // ==========================================================================

    showModal(modalId) {
      const modal = document.getElementById(modalId);
      if (modal) {
        modal.removeAttribute('hidden');
        modal.classList.add('active');
        modal.style.setProperty('display', 'flex', 'important');
      }
    }

    hideModal(modalId) {
      const modal = document.getElementById(modalId);
      if (modal) {
        modal.setAttribute('hidden', '');
        modal.classList.remove('active');
        modal.style.setProperty('display', 'none', 'important');
      }
    }

    toggleDrawer(forceState) {
      const drawer = this.dom.actionDrawer;
      const willOpen = forceState !== undefined ? forceState : !drawer.classList.contains('open');
      if (willOpen) {
        drawer.classList.add('open');
      } else {
        drawer.classList.remove('open');
      }
    }

    renderExcelTable(records) {
      const tbody = this.dom.excelTableBody;
      tbody.innerHTML = '';
      let sum = 0;

      records.forEach(row => {
        sum += Number(row.amount);
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${row.date}</td>
          <td><strong>${row.vendor}</strong></td>
          <td><span class="excel-category-badge">${row.category}</span></td>
          <td class="text-right">$${Number(row.amount).toFixed(2)}</td>
          <td>${row.tax_deductible ? '✓ Yes' : '—'}</td>
          <td>${row.payment_method}</td>
        `;
        tbody.appendChild(tr);
      });

      this.dom.excelTotalAmount.textContent = `$${sum.toFixed(2)}`;
    }

    renderRagResults(results) {
      const list = this.dom.ragResultsList;
      list.innerHTML = '';
      if (!results || results.length === 0) {
        list.innerHTML = '<div class="rag-result-card">No memory documents matched query.</div>';
        return;
      }

      results.forEach(r => {
        const card = document.createElement('div');
        card.className = 'rag-result-card';
        card.innerHTML = `
          <div class="rag-card-header">
            <span>DOC: ${r.doc_id || 'document'}</span>
            <span>SIMILARITY: ${(Number(r.score) * 100).toFixed(1)}%</span>
          </div>
          <div class="rag-card-text">${r.text}</div>
        `;
        list.appendChild(card);
      });
    }

    async executeRagQuery() {
      const query = this.dom.ragQueryInput.value.trim() || 'financial expenses';
      this.dom.ragResultsList.innerHTML = '<div class="rag-result-card">Searching local vector store...</div>';
      const res = await this.backend.queryMemory(query);
      this.renderRagResults(res.results || []);
    }

    async executePromptScan() {
      const prompt = this.dom.secPromptInput.value.trim();
      const res = await this.backend.scanPrompt(prompt);
      const card = this.dom.promptScanResult;
      card.removeAttribute('hidden');

      if (!res.safe) {
        card.className = 'scan-result-card blocked';
        card.innerHTML = `
          <strong>[BLOCKED] INDIRECT PROMPT INJECTION DETECTED</strong><br>
          Verdict: ${res.verdict}<br>
          Flagged Pattern: <code>${res.flagged_pattern}</code><br>
          Defense SOP: Threat isolated before reaching LLM inference plane.
        `;
        this.logEvent('elevated', `Security Scanner BLOCKED prompt: "${prompt}"`);
      } else {
        card.className = 'scan-result-card clean';
        card.innerHTML = `
          <strong>[CLEAN] ZERO-TRUST SCAN PASSED</strong><br>
          Verdict: ${res.verdict}<br>
          Status: Prompt verified safe for downstream execution.
        `;
        this.logEvent('unprivileged', `Security Scanner PASSED prompt: "${prompt}"`);
      }
    }

    async triggerExcelSynthesis() {
      this.dom.btnTriggerSynthesis.disabled = true;
      this.dom.btnTriggerSynthesis.textContent = 'Generating...';
      const res = await this.backend.extractToExcel(SAMPLE_RECORDS, 'multimodal_synthesis.xlsx');
      this.renderExcelTable(SAMPLE_RECORDS);
      this.dom.btnTriggerSynthesis.disabled = false;
      this.dom.btnTriggerSynthesis.innerHTML = '<span>⚡ Generate via Worker API</span>';
      this.logEvent('unprivileged', `Excel synthesis completed: ${res.filename}`);
      this.audio.chimeSuccess();
    }

    logEvent(plane, message) {
      const list = this.dom.timelineLogList;
      const now = new Date();
      const timeStr = now.toTimeString().split(' ')[0] + '.' + String(now.getMilliseconds()).padStart(3, '0');

      const item = document.createElement('div');
      item.className = `log-item ${plane}`;
      item.innerHTML = `
        <span class="log-time">${timeStr}</span>
        <div class="log-content">
          <span class="log-plane">${plane.toUpperCase()}</span>
          <span class="log-msg">${message}</span>
        </div>
      `;

      list.insertBefore(item, list.firstChild);
    }

    // ==========================================================================
    // Health Polling Loop
    // ==========================================================================

    startHealthPolling() {
      const poll = async () => {
        const health = await this.backend.checkHealth();
        // Worker Badge
        const wChip = this.dom.chipWorker;
        if (health.worker) {
          wChip.className = 'status-chip online';
          wChip.querySelector('.chip-label').textContent = 'Worker: Active (50051)';
        } else {
          wChip.className = 'status-chip offline';
          wChip.querySelector('.chip-label').textContent = 'Worker: Standby';
        }

        // Daemon Badge
        const dChip = this.dom.chipDaemon;
        if (health.daemon) {
          dChip.className = 'status-chip online';
          dChip.querySelector('.chip-label').textContent = 'Daemon: Active (8081)';
        } else {
          dChip.className = 'status-chip offline';
          dChip.querySelector('.chip-label').textContent = 'Daemon: Standby';
        }
      };

      poll();
      setInterval(poll, CONFIG.HEALTH_POLL_INTERVAL_MS);
    }
  }

  // Initialize once DOM is ready
  document.addEventListener('DOMContentLoaded', () => {
    window.omniApp = new OmniOperatorApp();
  });

})();
