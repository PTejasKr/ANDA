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

    demoStatusText.textContent = '🧠 Processing command...';
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
          demoStatusText.innerHTML = `✅ [${action}]: Opening <a href="${data.target_url}" target="_blank" rel="noopener noreferrer" style="color:#38BDF8;text-decoration:underline;font-weight:700;">${data.target_url} ↗</a> <span style="color:#94A3B8;font-size:12px;">(Click link if popup blocked)</span>`;
        } else if (data.system_uri) {
          try { window.location.href = data.system_uri; } catch (e) {}
          demoStatusText.innerHTML = `⚙️ [${action}]: Dispatched <a href="${data.system_uri}" style="color:#38BDF8;text-decoration:underline;font-weight:700;">${data.system_uri}</a> <span style="color:#94A3B8;font-size:12px;">(Click to trigger system handler)</span>`;
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

    // --------------------------------------------------------------------------
    // Spotlight Search Engine (Apps, Games, Math, Settings, Web Fallback)
    // --------------------------------------------------------------------------
    const spotlightOverlay = document.getElementById('spotlightOverlay');
    const spotlightList = document.getElementById('spotlightList');
    let spotlightResults = [];
    let spotlightSelectedIdx = 0;

    const SYSTEM_INDEXED_ITEMS = [
      { category: 'GAME', title: 'Cyberpunk 2077', sub: 'C:\\ProgramData\\...\\Cyberpunk 2077.lnk', action: 'launch_game', target: 'Cyberpunk 2077' },
      { category: 'APP', title: 'Visual Studio Code', sub: 'Code.exe • Development IDE', action: 'launch_app', target: 'Visual Studio Code' },
      { category: 'APP', title: 'Google Chrome', sub: 'chrome.exe • Web Browser', action: 'launch_app', target: 'Google Chrome' },
      { category: 'APP', title: 'Calculator', sub: 'calc • Windows Native Tool', action: 'launch_app', target: 'calc' },
      { category: 'SETTING', title: 'Sound & Audio Settings', sub: 'ms-settings:sound', action: 'open_setting', target: 'ms-settings:sound' },
      { category: 'SETTING', title: 'Task Manager', sub: 'taskmgr • System Resource Monitor', action: 'open_setting', target: 'taskmgr' },
      { category: 'FILE', title: 'Financial_Report_Q4.xlsx', sub: 'Documents\\Financials', action: 'open_file', target: 'Financial_Report_Q4.xlsx' },
    ];

    function evalMath(expr) {
      const clean = expr.trim().replace(/\^/g, '**');
      const pct = clean.match(/^(\d+(?:\.\d+)?)\s*%\s*(?:of)?\s*(\d+(?:\.\d+)?)$/i);
      if (pct) {
        return (parseFloat(pct[1]) / 100.0) * parseFloat(pct[2]);
      }
      if (!/^[\d\s\+\-\*\/\(\)\.\%]+$/.test(clean) && !clean.includes('sqrt')) return null;
      try {
        const sanitized = clean.replace(/sqrt\(([^)]+)\)/g, 'Math.sqrt($1)');
        // Safe evaluation of pure numbers and arithmetic operators
        const fn = new Function(`return (${sanitized})`);
        const res = fn();
        if (typeof res === 'number' && !isNaN(res) && isFinite(res)) {
          return res;
        }
      } catch (e) {}
      return null;
    }

    function querySpotlight(q) {
      const query = q.trim();
      if (!query) return [];
      const lower = query.toLowerCase();
      const results = [];

      // 1. Math calculation
      const mathVal = evalMath(query);
      if (mathVal !== null) {
        const formatted = Number.isInteger(mathVal) ? mathVal.toString() : mathVal.toFixed(3).replace(/\.?0+$/, '');
        results.push({
          category: 'MATH',
          title: `${query} = ${formatted}`,
          sub: 'Instant Calculation Result (Press Enter to Copy)',
          action: 'math',
          target: formatted
        });
      }

      // 2. Apps & Games
      let cleanTarget = lower;
      for (const p of ['open a game ', 'open the game ', 'play the game ', 'launch the game ', 'open ', 'play ', 'launch ', 'start ']) {
        if (cleanTarget.startsWith(p)) {
          cleanTarget = cleanTarget.slice(p.length).trim();
          break;
        }
      }

      for (const item of SYSTEM_INDEXED_ITEMS) {
        const itemLower = item.title.toLowerCase();
        if (itemLower === cleanTarget || itemLower.includes(cleanTarget) || cleanTarget.includes(itemLower)) {
          results.push(item);
        }
      }

      // 3. Web Search Fallback
      results.push({
        category: 'WEB',
        title: `Search the web for "${query}"`,
        sub: 'Google Search in Default Browser',
        action: 'web_search',
        target: `https://www.google.com/search?q=${encodeURIComponent(query)}`
      });

      return results.slice(0, 5);
    }

    function renderSpotlightResults() {
      if (!spotlightOverlay || !spotlightList) return;
      spotlightList.innerHTML = '';

      if (spotlightResults.length === 0) {
        spotlightOverlay.classList.remove('active');
        return;
      }

      spotlightOverlay.classList.add('active');

      spotlightResults.forEach((item, idx) => {
        const row = document.createElement('div');
        row.className = `spotlight-item ${idx === spotlightSelectedIdx ? 'selected' : ''}`;
        row.innerHTML = `
          <div class="spotlight-item-left">
            <span class="spotlight-cat-badge">${item.category}</span>
            <span class="spotlight-item-title">${item.title}</span>
          </div>
          <span class="spotlight-item-sub">${item.sub}</span>
        `;
        row.addEventListener('click', () => {
          spotlightSelectedIdx = idx;
          executeSpotlightSelection(item);
        });
        spotlightList.appendChild(row);
      });
    }

    function executeSpotlightSelection(item) {
      if (!item) return;
      spotlightOverlay.classList.remove('active');
      spotlightResults = [];

      if (item.action === 'launch_game') {
        demoStatusText.innerHTML = `🎮 <strong>Launched Game:</strong> ${item.title} (${item.sub})`;
        demoStatusText.style.color = '#10B981';
      } else if (item.action === 'launch_app') {
        demoStatusText.innerHTML = `🚀 <strong>Launched Application:</strong> ${item.title}`;
        demoStatusText.style.color = '#10B981';
      } else if (item.action === 'open_setting') {
        try { window.location.href = item.target; } catch (e) {}
        demoStatusText.innerHTML = `⚙️ <strong>Opened System Setting:</strong> <a href="${item.target}" style="color:#38BDF8;text-decoration:underline;">${item.title}</a>`;
        demoStatusText.style.color = '#10B981';
      } else if (item.action === 'math') {
        try { navigator.clipboard.writeText(item.target); } catch (e) {}
        demoStatusText.innerHTML = `🔢 <strong>Calculation:</strong> ${item.title} (Copied)`;
        demoStatusText.style.color = '#10B981';
      } else if (item.action === 'web_search') {
        try { window.open(item.target, '_blank'); } catch (e) {}
        demoStatusText.innerHTML = `🌐 <strong>Web Search:</strong> <a href="${item.target}" target="_blank" style="color:#38BDF8;text-decoration:underline;">${item.title} ↗</a>`;
        demoStatusText.style.color = '#10B981';
      } else {
        demoStatusText.innerHTML = `✅ <strong>Executed:</strong> ${item.title}`;
        demoStatusText.style.color = '#10B981';
      }

      setTimeout(() => {
        demoStatusText.textContent = 'Ready • Press [Left Ctrl + Win] anywhere to summon';
        demoStatusText.style.color = '#64748B';
      }, 5000);
    }

    function fallbackDemoExecution(prompt) {
      const q = (prompt || '').trim();
      if (!q) return;

      const matches = querySpotlight(q);
      if (matches && matches.length > 0) {
        executeSpotlightSelection(matches[0]);
        return;
      }

      const res = resolveWebSearch(q);
      try { window.open(res.url, '_blank'); } catch (e) {}
      demoStatusText.innerHTML = `🌐 <strong>Search Executed:</strong> <a href="${res.url}" target="_blank" style="color:#38BDF8;text-decoration:underline;">${res.query} ↗</a>`;
      demoStatusText.style.color = '#10B981';
      setTimeout(() => {
        demoStatusText.textContent = 'Ready • Press [Left Ctrl + Win] anywhere to summon';
        demoStatusText.style.color = '#64748B';
      }, 5000);
    }

    if (demoInput) {
      demoInput.addEventListener('input', () => {
        const q = demoInput.value.trim();
        spotlightResults = querySpotlight(q);
        spotlightSelectedIdx = 0;
        renderSpotlightResults();
      });

      demoInput.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowDown') {
          if (spotlightResults.length > 0) {
            e.preventDefault();
            spotlightSelectedIdx = (spotlightSelectedIdx + 1) % spotlightResults.length;
            renderSpotlightResults();
          }
        } else if (e.key === 'ArrowUp') {
          if (spotlightResults.length > 0) {
            e.preventDefault();
            spotlightSelectedIdx = (spotlightSelectedIdx - 1 + spotlightResults.length) % spotlightResults.length;
            renderSpotlightResults();
          }
        } else if (e.key === 'Escape') {
          spotlightOverlay.classList.remove('active');
          spotlightResults = [];
        } else if (e.key === 'Enter') {
          if (spotlightResults.length > 0 && spotlightSelectedIdx < spotlightResults.length) {
            e.preventDefault();
            executeSpotlightSelection(spotlightResults[spotlightSelectedIdx]);
          } else {
            executeDemoPrompt(demoInput.value);
          }
        }
      });
    }

    if (demoSendBtn) {
      demoSendBtn.addEventListener('click', () => {
        if (spotlightResults.length > 0 && spotlightSelectedIdx < spotlightResults.length) {
          executeSpotlightSelection(spotlightResults[spotlightSelectedIdx]);
        } else {
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
    'Open YouTube in default browser',
    'Search quantum computing on the internet',
    'Open sound settings',
    'Stage and organize my pending downloads',
    'Recall vector memory for Q4 cloud expenses'
  ];
  let samplePromptIdx = 0;

  const timerMin = document.getElementById('timerMin');
  const timerSec = document.getElementById('timerSec');
  let timerInterval = null;
  let timerElapsedSeconds = 0;

  function startDurationTimer() {
    clearInterval(timerInterval);
    timerElapsedSeconds = 0;
    updateTimerDisplay(0);
    timerInterval = setInterval(() => {
      timerElapsedSeconds++;
      updateTimerDisplay(timerElapsedSeconds);
    }, 1000);
  }

  function stopDurationTimer() {
    clearInterval(timerInterval);
    setTimeout(() => {
      if (!isListening) {
        if (timerMin) timerMin.textContent = '00';
        if (timerSec) timerSec.textContent = '03';
      }
    }, 3000);
  }

  function updateTimerDisplay(totalSeconds) {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    if (timerMin) timerMin.textContent = String(mins).padStart(2, '0');
    if (timerSec) timerSec.textContent = String(secs).padStart(2, '0');
  }

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
        startDurationTimer();
        demoStatusText.textContent = '🎙️ Listening... Speak your command';
        demoStatusText.style.color = '#FF4D5A';
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
        stopDurationTimer();
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
        stopDurationTimer();
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
      startDurationTimer();
      demoStatusText.textContent = '🎙️ Recording voice... Click mic when done to enter';
      demoStatusText.style.color = '#FF4D5A';

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        demoMicBtn.classList.remove('active');
        isListening = false;
        stopDurationTimer();

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
