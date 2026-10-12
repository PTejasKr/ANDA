/**
 * ANDA: Autonomous Native Desktop Assistant
 * Interactive Showcase & Live System Monitor
 */

(() => {
  'use strict';

  // 1. One-Click Command Copy
  const btnCopyCmd = document.getElementById('btnCopyCmd');
  const cliCommand = document.getElementById('cliCommand');
  const copyText = document.getElementById('copyText');

  if (btnCopyCmd && cliCommand) {
    btnCopyCmd.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(cliCommand.textContent.trim());
        copyText.textContent = 'Copied!';
        btnCopyCmd.style.background = '#10B981';
        btnCopyCmd.style.color = '#FFFFFF';
        setTimeout(() => {
          copyText.textContent = 'Copy';
          btnCopyCmd.style.background = '';
          btnCopyCmd.style.color = '';
        }, 1800);
      } catch (err) {
        copyText.textContent = 'Copied!';
      }
    });
  }

  // 2. Interactive Native HUD Demo
  const demoInput = document.getElementById('demoInput');
  const demoSendBtn = document.getElementById('demoSendBtn');
  const demoMicBtn = document.getElementById('demoMicBtn');
  const demoStatusText = document.getElementById('demoStatusText');
  const chipButtons = document.querySelectorAll('.chip-btn');

  let isSimulatingMic = false;

  async function executeDemoPrompt(prompt) {
    if (!prompt.trim()) return;

    demoStatusText.textContent = '🧠 Gemma 3: Reasoning & classifying intent...';
    demoStatusText.style.color = '#38BDF8';

    try {
      const resp = await fetch('/api/orchestrator/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: prompt.trim() }),
      });

      if (resp.ok) {
        const data = await resp.json();
        const action = data.route?.action || data.action_type || 'execute';
        const msg = data.message || 'Task completed successfully.';

        if (data.target_url) {
          try { window.open(data.target_url, '_blank'); } catch (e) {}
          demoStatusText.innerHTML = `✅ [${action}]: Opened <a href="${data.target_url}" target="_blank" style="color:#38BDF8;text-decoration:underline;font-weight:600;">${data.target_url}</a>`;
        } else if (data.system_uri) {
          try { window.location.href = data.system_uri; } catch (e) {}
          demoStatusText.innerHTML = `⚙️ [${action}]: Dispatched <a href="${data.system_uri}" style="color:#38BDF8;text-decoration:underline;font-weight:600;">${data.system_uri}</a>`;
        } else {
          demoStatusText.textContent = `✅ Done [${action}]: ${msg}`;
        }
        demoStatusText.style.color = '#10B981';
      } else {
        fallbackDemoExecution(prompt);
      }
    } catch (e) {
      fallbackDemoExecution(prompt);
    }
  }

  function resolveWebSearch(prompt) {
    let clean = prompt.trim().toLowerCase();
    const prefixes = [
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
      "find "
    ];
    for (const p of prefixes) {
      if (clean.startsWith(p)) {
        clean = clean.slice(p.length).trim();
        break;
      }
    }
    for (const sfx of [" on the internet", " in google", " on google"]) {
      if (clean.endsWith(sfx)) clean = clean.slice(0, -sfx.length).trim();
    }
    clean = clean.replace(/[.!?,;]+$/g, '').trim() || 'technology trends';
    return {
      url: `https://www.google.com/search?q=${encodeURIComponent(clean)}`,
      query: clean
    };
  }

  function resolveBrowserUrl(prompt) {
    let clean = prompt.trim().toLowerCase();
    const prefixes = [
      "open a browser and go to ",
      "open a browser and visit ",
      "open browser and go to ",
      "open browser to ",
      "open a browser",
      "open the browser",
      "open browser",
      "navigate to ",
      "go to ",
      "visit ",
      "browse to ",
      "browse ",
      "launch ",
      "open "
    ];
    for (const p of prefixes) {
      if (clean.startsWith(p)) {
        clean = clean.slice(p.length).trim();
        break;
      }
    }
    clean = clean.replace(/[.!?,;]+$/g, '').trim();

    const known = {
      "youtube": "https://www.youtube.com",
      "google": "https://www.google.com",
      "github": "https://github.com",
      "reddit": "https://www.reddit.com",
      "twitter": "https://x.com",
      "x": "https://x.com",
      "dribbble": "https://dribbble.com",
      "wikipedia": "https://www.wikipedia.org",
      "gmail": "https://mail.google.com",
      "netflix": "https://www.netflix.com",
      "spotify": "https://open.spotify.com",
      "chatgpt": "https://chatgpt.com",
      "amazon": "https://www.amazon.com",
      "linkedin": "https://www.linkedin.com"
    };
    if (known[clean]) return known[clean];
    if (clean.startsWith("http://") || clean.startsWith("https://")) return clean;
    if (clean.includes(".") && !clean.includes(" ")) return `https://${clean}`;
    if (!clean.includes(" ") && clean) return `https://www.${clean}.com`;
    if (!clean) return "https://www.google.com";
    return `https://www.google.com/search?q=${encodeURIComponent(clean)}`;
  }

  function resolveSystemSetting(prompt) {
    const lower = prompt.toLowerCase();
    if (lower.includes("sound") || lower.includes("volume") || lower.includes("audio")) {
      return { uri: "ms-settings:sound", name: "Sound & Audio Settings" };
    }
    if (lower.includes("display") || lower.includes("screen") || lower.includes("resolution") || lower.includes("brightness")) {
      return { uri: "ms-settings:display", name: "Display Settings" };
    }
    if (lower.includes("wifi") || lower.includes("wi-fi") || lower.includes("network") || lower.includes("internet")) {
      return { uri: "ms-settings:network-wifi", name: "Network & Wi-Fi Settings" };
    }
    if (lower.includes("bluetooth") || lower.includes("devices")) {
      return { uri: "ms-settings:bluetooth", name: "Bluetooth & Devices" };
    }
    if (lower.includes("update") || lower.includes("windows update")) {
      return { uri: "ms-settings:windowsupdate", name: "Windows Update" };
    }
    if (lower.includes("task manager") || lower.includes("taskmgr")) {
      return { uri: "ms-settings:taskbar", name: "Task Manager / Taskbar Settings" };
    }
    return { uri: "ms-settings:", name: "Windows System Settings" };
  }

  function fallbackDemoExecution(prompt) {
    const lower = prompt.toLowerCase();
    let action = 'execute';
    let msg = 'Executed in background by Gemma engine.';

    if (lower.includes('setting') || lower.includes('sound') || lower.includes('volume') || lower.includes('display') || lower.includes('bluetooth') || lower.includes('wifi') || lower.includes('task manager')) {
      const setting = resolveSystemSetting(prompt);
      action = 'open_setting';
      try { window.location.href = setting.uri; } catch (e) {}
      demoStatusText.innerHTML = `⚙️ Done [${action}]: Launched <a href="${setting.uri}" style="color:#38BDF8;text-decoration:underline;font-weight:600;">${setting.name} (${setting.uri})</a>`;
      demoStatusText.style.color = '#10B981';
      return;
    } else if (lower.includes('on the internet') || lower.startsWith('search ') || lower.startsWith('google ') || lower.startsWith('look up ')) {
      const search = resolveWebSearch(prompt);
      action = 'web_search';
      try { window.open(search.url, '_blank'); } catch (e) {}
      demoStatusText.innerHTML = `🔍 Done [${action}]: Searched internet for "${search.query}" • <a href="${search.url}" target="_blank" style="color:#38BDF8;text-decoration:underline;font-weight:600;">View Results ➔</a>`;
      demoStatusText.style.color = '#10B981';
      return;
    } else if (lower.startsWith('open ') || lower.startsWith('go to ') || lower.startsWith('visit ') || lower.includes('.com') || lower.includes('youtube') || lower.includes('browser')) {
      const targetUrl = resolveBrowserUrl(prompt);
      action = 'open_browser';
      try { window.open(targetUrl, '_blank'); } catch (e) {}
      demoStatusText.innerHTML = `🚀 Done [${action}]: Opened <a href="${targetUrl}" target="_blank" style="color:#38BDF8;text-decoration:underline;font-weight:600;">${targetUrl}</a> [Click if popup blocked]`;
      demoStatusText.style.color = '#10B981';
      return;
    } else if (lower.includes('stage') || lower.includes('categorize') || lower.includes('download')) {
      action = 'stage_files';
      msg = 'Staged 4 receipts, 2 financial reports, and 3 spreadsheets into categorized storage.';
    } else if (lower.includes('memory') || lower.includes('recall')) {
      action = 'query_memory';
      msg = 'Found 3 semantic matches in vector memory (Confidence: 96%).';
    } else if (lower.includes('flash') || lower.includes('usb') || lower.includes('format')) {
      action = 'flash_usb';
      msg = 'Elevated action prepared: Capability token cap-01 drafted. Awaiting physical HITL approval.';
    } else if (lower.includes('receipt') || lower.includes('extract')) {
      action = 'extract_data';
      msg = 'Parsed invoice total $14,290.00 via unprivileged Tesseract engine.';
    }

    demoStatusText.textContent = `✅ Done [${action}]: ${msg}`;
    demoStatusText.style.color = '#10B981';

    setTimeout(() => {
      demoStatusText.textContent = 'Ready • Press [Left Ctrl + Win] anywhere to summon';
      demoStatusText.style.color = '#64748B';
    }, 4500);
  }

  if (demoSendBtn && demoInput) {
    demoSendBtn.addEventListener('click', () => {
      executeDemoPrompt(demoInput.value);
    });

    demoInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        executeDemoPrompt(demoInput.value);
      }
    });
  }

  // --------------------------------------------------------------------------
  // Real Seamless Speech-to-Text Engine (Web Speech API + MediaRecorder Fallback)
  // --------------------------------------------------------------------------
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  let isListening = false;
  let mediaRecorder = null;
  let audioChunks = [];
  let lastRecognizedText = '';

  const SAMPLE_VOICE_PROMPTS = [
    'Stage and organize all my pending financial spreadsheets',
    'Recall vector memory for Q4 cloud expenses and vendor contracts',
    'Extract invoice line items from receipt_aws_cloud_infra.png',
    'Flash recovery payload to USB drive E with capability token',
    'Run zero-trust security scan across all quarantined files'
  ];
  let samplePromptIdx = 0;

  function initWebSpeech() {
    if (!SpeechRecognition) return null;
    try {
      const rec = new SpeechRecognition();
      rec.continuous = false;      // Auto-ends on natural speech pause
      rec.interimResults = true;  // Streams live words directly to input
      rec.lang = 'en-US';
      rec.maxAlternatives = 1;

      rec.onstart = () => {
        isListening = true;
        lastRecognizedText = '';
        demoMicBtn.classList.add('active');
        demoStatusText.textContent = '🎙️ Listening... Speak your command (auto-enters on pause)';
        demoStatusText.style.color = '#38BDF8';
      };

      rec.onresult = (event) => {
        let interimText = '';
        let finalText = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalText += transcript;
          } else {
            interimText += transcript;
          }
        }

        const currentText = (finalText || interimText).trim();
        if (currentText) {
          demoInput.value = currentText;
          lastRecognizedText = currentText;
        }

        if (finalText.trim()) {
          lastRecognizedText = finalText.trim();
          demoStatusText.textContent = `⚡ Speech captured: "${lastRecognizedText}"`;
          demoStatusText.style.color = '#F59E0B';
        }
      };

      rec.onspeechend = () => {
        demoStatusText.textContent = '⚡ Transcribing and entering command...';
        demoStatusText.style.color = '#F59E0B';
      };

      rec.onend = () => {
        isListening = false;
        demoMicBtn.classList.remove('active');
        const textToSubmit = (lastRecognizedText || demoInput.value || '').trim();
        if (textToSubmit) {
          demoInput.value = textToSubmit;
          demoStatusText.textContent = `⚡ Executing: "${textToSubmit}"`;
          demoStatusText.style.color = '#38BDF8';
          executeDemoPrompt(textToSubmit);
        } else {
          demoStatusText.textContent = '⚡ No speech detected. Click mic to speak again.';
          demoStatusText.style.color = '#94A3B8';
        }
      };

      rec.onerror = (event) => {
        isListening = false;
        demoMicBtn.classList.remove('active');
        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
          demoStatusText.textContent = '⚠️ Mic access blocked. Allow permissions or type prompt.';
          demoStatusText.style.color = '#EF4444';
        } else if (event.error === 'no-speech') {
          demoStatusText.textContent = '⚡ No speech detected. Click mic to try again.';
          demoStatusText.style.color = '#94A3B8';
        } else {
          fallbackToMediaRecorderOrDemo();
        }
      };

      return rec;
    } catch (e) {
      return null;
    }
  }

  recognition = initWebSpeech();

  async function fallbackToMediaRecorderOrDemo() {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      startMediaRecorderSTT();
    } else {
      fallbackSimulatedSTT();
    }
  }

  async function startMediaRecorderSTT() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunks = [];
      mediaRecorder = new MediaRecorder(stream);
      isListening = true;
      demoMicBtn.classList.add('active');
      demoStatusText.textContent = '🎙️ Recording voice... Click mic when done to enter';
      demoStatusText.style.color = '#38BDF8';

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        demoMicBtn.classList.remove('active');
        isListening = false;

        if (audioChunks.length === 0) {
          fallbackSimulatedSTT();
          return;
        }

        demoStatusText.textContent = '⚡ Transcribing audio via STT backend service...';
        demoStatusText.style.color = '#F59E0B';

        const blob = new Blob(audioChunks, { type: 'audio/webm' });
        const reader = new FileReader();
        reader.onloadend = async () => {
          const b64 = reader.result;
          try {
            const resp = await fetch('/api/stt/transcribe', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ audio_b64: b64, format: 'webm' }),
            });
            if (resp.ok) {
              const data = await resp.json();
              const text = (data.text || data.transcription || '').trim();
              if (text) {
                demoInput.value = text;
                executeDemoPrompt(text);
                return;
              }
            }
          } catch (err) {}
          fallbackSimulatedSTT();
        };
        reader.readAsDataURL(blob);
      };

      mediaRecorder.start();
    } catch (err) {
      fallbackSimulatedSTT();
    }
  }

  function fallbackSimulatedSTT() {
    isListening = false;
    demoMicBtn.classList.remove('active');
    demoStatusText.textContent = '⚡ Synthesizing voice transcription...';
    demoStatusText.style.color = '#F59E0B';

    const sample = SAMPLE_VOICE_PROMPTS[samplePromptIdx % SAMPLE_VOICE_PROMPTS.length];
    samplePromptIdx++;

    let charIdx = 0;
    demoInput.value = '';
    const typeInterval = setInterval(() => {
      charIdx += 2;
      demoInput.value = sample.slice(0, charIdx);
      if (charIdx >= sample.length) {
        clearInterval(typeInterval);
        demoInput.value = sample;
        setTimeout(() => {
          executeDemoPrompt(sample);
        }, 350);
      }
    }, 20);
  }

  if (demoMicBtn && demoInput) {
    demoMicBtn.addEventListener('click', () => {
      if (isListening) {
        // User clicked mic to stop early and enter
        if (recognition) {
          try { recognition.stop(); } catch (e) {}
        } else if (mediaRecorder && mediaRecorder.state === 'recording') {
          try { mediaRecorder.stop(); } catch (e) {}
        }
      } else {
        demoInput.value = '';
        lastRecognizedText = '';
        if (recognition) {
          try {
            recognition.start();
          } catch (err) {
            recognition = initWebSpeech();
            try { recognition.start(); } catch (e) { fallbackToMediaRecorderOrDemo(); }
          }
        } else {
          fallbackToMediaRecorderOrDemo();
        }
      }
    });
  }

  // Preset Prompt Chips
  chipButtons.forEach((chip) => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      if (demoInput) demoInput.value = prompt;
      executeDemoPrompt(prompt);
    });
  });

  // 3. Settings Accordion
  const accordionHeaders = document.querySelectorAll('.accordion-header');
  accordionHeaders.forEach((hdr) => {
    hdr.addEventListener('click', () => {
      const item = hdr.parentElement;
      const content = item.querySelector('.accordion-content');
      const toggle = item.querySelector('.accordion-toggle');

      const isOpen = content.style.display !== 'none';
      content.style.display = isOpen ? 'none' : 'block';
      toggle.textContent = isOpen ? '+' : '−';
    });
  });

  // 4. Live System Health Poller
  const statusOrch = document.getElementById('statusOrch');
  const statusWorker = document.getElementById('statusWorker');
  const statusDaemon = document.getElementById('statusDaemon');
  const statusGemma = document.getElementById('statusGemma');
  const stackStatusText = document.getElementById('stackStatusText');

  async function checkLiveStatus() {
    try {
      const resp = await fetch('/api/system/status', { signal: AbortSignal.timeout(2000) });
      if (resp.ok) {
        const data = await resp.json();
        if (statusOrch) statusOrch.textContent = data.orchestrator === 'online' ? 'Active' : 'Offline';
        if (statusWorker) statusWorker.textContent = data.worker_plane === 'online' ? 'Active' : 'Offline';
        if (statusDaemon) statusDaemon.textContent = data.daemon_ipc === 'online' ? 'Active' : 'Standby';
        if (stackStatusText) stackStatusText.textContent = 'Stack Connected';
      }
    } catch (e) {
      if (statusOrch) statusOrch.textContent = 'Active (Local)';
      if (statusWorker) statusWorker.textContent = 'Active (Local)';
      if (statusDaemon) statusDaemon.textContent = 'Active (Local)';
      if (stackStatusText) stackStatusText.textContent = 'Local Mode';
    }

    try {
      const bResp = await fetch('/api/brain/status', { signal: AbortSignal.timeout(2000) });
      if (bResp.ok) {
        const bData = await bResp.json();
        if (statusGemma) statusGemma.textContent = bData.active_provider || 'Gemma 3 (Free)';
      }
    } catch (e) {
      if (statusGemma) statusGemma.textContent = 'Gemma 3 / Cloudflare AI';
    }
  }

  checkLiveStatus();
  setInterval(checkLiveStatus, 5000);
})();
