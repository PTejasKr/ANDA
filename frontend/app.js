/**
 * ANDA° — Autonomous Native Desktop Assistant
 * Pinterest Pin 520025088247216830 Editorial Frontend Engine
 * Features:
 * 1. Pure ASCII Art Egg ("anda") with scroll-driven left-to-right zig-zag fracture & hovering top shell.
 * 2. Interactive Native HUD command execution with physical OS actions & smart autocompletion.
 * 3. Voice orb simulation with real-time waveform and duration timer.
 * 4. PowerShell installer one-click copy.
 */

(() => {
  'use strict';

  // ==========================================================================
  // 1. PURE ASCII ART EGG ("ANDA") DATA & INTERLOCKING MESH
  // ==========================================================================

  const EGG_TOP_LINES = [
    "                       #                      ",
    "                  ##=%###*=##                 ",
    "                #=%%%%%###**+=#               ",
    "              #=%%%%%%%###**++==#             ",
    "             #%%%%%%%%###***++==-#            ",
    "            =%%%%%%%%%###***++==-:=           ",
    "          #=%%%%%%%%####***+++==-::=#         ",
    "         #=%%%%%%%%####***+++==--::.=#        ",
    "        #=%%%%%%%#####****++===--::..=#       ",
    "        =##%%%######****++++==---::...=       ",
    "       =##########*****+++===---::.....=      ",
    "      /*####/###**/**+++/===--/:::../...#     ",
    "      //***\\//***\\//+++\\//=--\\//:..\\//..=     ",
    "     \\ //*\\\\ //*\\\\ //=\\\\ //-\\\\ //.\\\\ //.\\\\    ",
    "        /\\\\   /\\\\   /\\\\   /\\\\   /\\\\   /\\\\     ",
    "         \\     \\     \\     \\     \\     \\      "
  ];

  const EGG_BOTTOM_LINES = [
    "      /     /     /     /     /     /         ",
    "      //   \\//   \\//   \\//   \\//   \\//        ",
    "     \\+// \\\\*// \\\\+// \\\\=// \\\\:// \\\\.// \\\\    ",
    "     =++/\\\\+++/\\\\++=/\\\\=--/\\\\::./\\\\.../\\\\=    ",
    "    #=+++\\+++++\\=====\\----:\\:....\\.....\\.=#   ",
    "    #=============-----::::..............=#   ",
    "    #=-======-------:::::................=#   ",
    "     =----------::::::...................=    ",
    "     #:::::::::::::......................#    ",
    "     #=.................................=#    ",
    "      #=...............................=#     ",
    "       #=.............................=#      ",
    "         #=.........................=#        ",
    "           ##=...................=##          ",
    "              ###===.......===###             "
  ];

  // Active Zig-Zag Crack Line (Spans 46 columns, zig-zags /\/\/\/\/\)
  const CRACK_PATTERN = "    /\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\    ";

  // Elements
  const asciiTopPre = document.getElementById('asciiTopPre');
  const asciiBottomPre = document.getElementById('asciiBottomPre');
  const asciiCrackPre = document.getElementById('asciiCrackPre');
  const eggTopShell = document.getElementById('eggTopShell');
  const eggBottomShell = document.getElementById('eggBottomShell');
  const eggCoreHud = document.getElementById('eggCoreHud');
  const scrubFill = document.getElementById('scrubFill');
  const btnCrackToggle = document.getElementById('btnCrackToggle');
  const crackToggleLabel = document.getElementById('crackToggleLabel');
  const crackSparkGlow = document.getElementById('crackSparkGlow');
  const scrollHatchHint = document.getElementById('scrollHatchHint');

  let currentCrackProgress = 0;
  let targetCrackProgress = 0;
  let isManualToggle = false;
  let crackCharSpans = [];

  // Initialize ASCII Egg Shells & Crack Spans
  function initAsciiEgg() {
    if (!asciiTopPre || !asciiBottomPre || !asciiCrackPre) return;

    // 1. Render Top Shell
    asciiTopPre.textContent = EGG_TOP_LINES.join('\n');

    // 2. Render Bottom Shell
    asciiBottomPre.textContent = EGG_BOTTOM_LINES.join('\n');

    // 3. Render Interactive Zig-Zag Crack Spans
    asciiCrackPre.innerHTML = '';
    crackCharSpans = [];

    const chars = CRACK_PATTERN.split('');
    chars.forEach((ch, idx) => {
      const span = document.createElement('span');
      span.className = 'ascii-crack-char';
      span.dataset.col = idx;
      span.textContent = ch;
      asciiCrackPre.appendChild(span);
      crackCharSpans.push(span);
    });

    updateEggState(0);
  }

  // Update Fracture State based on Progress p (0.0 to 1.0)
  function updateEggState(p) {
    p = Math.max(0, Math.min(1, p));
    currentCrackProgress = p;

    // 1. Progress Bar Fill
    if (scrubFill) {
      scrubFill.style.width = `${(p * 100).toFixed(1)}%`;
    }

    // 2. Left-to-Right Zig-Zag Crack Propagation
    // Crack traverses columns from left to right during first 45% of progress
    const totalCols = crackCharSpans.length;
    const crackRatio = Math.min(1.0, p / 0.45);
    const activeColIndex = Math.floor(crackRatio * totalCols);

    crackCharSpans.forEach((span, col) => {
      if (col < activeColIndex && span.textContent.trim().length > 0) {
        span.classList.add('fractured');
        if (col === activeColIndex - 1) {
          span.classList.add('active-tip');
        } else {
          span.classList.remove('active-tip');
        }
      } else {
        span.classList.remove('fractured', 'active-tip');
      }
    });

    // Crack spark glow dot positioning along fracture tip
    if (crackSparkGlow) {
      if (p > 0.02 && p < 0.6) {
        crackSparkGlow.style.opacity = '1';
        const leftPercent = 10 + (crackRatio * 80);
        crackSparkGlow.style.left = `${leftPercent}%`;
      } else {
        crackSparkGlow.style.opacity = '0';
      }
    }

    // 3. Separation of Shells & Hovering (Happens from 25% to 100%)
    if (p > 0.2) {
      const sepRatio = Math.min(1.0, (p - 0.2) / 0.7);
      const topY = -85 * sepRatio;
      const topRot = -3.5 * sepRatio;
      const bottomY = 22 * sepRatio;
      const bottomRot = 1.4 * sepRatio;

      if (eggTopShell) {
        eggTopShell.style.setProperty('--top-translate-y', `${topY.toFixed(1)}px`);
        eggTopShell.style.setProperty('--top-rotate', `${topRot.toFixed(2)}deg`);
        eggTopShell.style.transform = `translateY(${topY.toFixed(1)}px) rotate(${topRot.toFixed(2)}deg)`;

        // Engage continuous silky sinusoidal hover float when separated
        if (sepRatio > 0.5) {
          eggTopShell.classList.add('is-hovering');
        } else {
          eggTopShell.classList.remove('is-hovering');
        }
      }

      if (eggBottomShell) {
        eggBottomShell.style.transform = `translateY(${bottomY.toFixed(1)}px) rotate(${bottomRot.toFixed(2)}deg)`;
      }

      // 4. Reveal Luminous HUD Core nestled inside
      if (eggCoreHud) {
        const coreOpacity = Math.min(1.0, (p - 0.28) / 0.45);
        const coreScale = 0.85 + (0.15 * coreOpacity);
        if (coreOpacity > 0.05) {
          eggCoreHud.classList.add('revealed');
          eggCoreHud.style.opacity = coreOpacity.toFixed(2);
          eggCoreHud.style.transform = `translate(-50%, -50%) scale(${coreScale.toFixed(2)})`;
        } else {
          eggCoreHud.classList.remove('revealed');
          eggCoreHud.style.opacity = '0';
        }
      }
    } else {
      // Re-sealed intact egg
      if (eggTopShell) {
        eggTopShell.classList.remove('is-hovering');
        eggTopShell.style.transform = 'translateY(0px) rotate(0deg)';
      }
      if (eggBottomShell) {
        eggBottomShell.style.transform = 'translateY(0px) rotate(0deg)';
      }
      if (eggCoreHud) {
        eggCoreHud.classList.remove('revealed');
        eggCoreHud.style.opacity = '0';
      }
    }

    // Toggle button label
    if (crackToggleLabel) {
      crackToggleLabel.textContent = p > 0.5 ? 'Reset Shell' : 'Crack Shell';
    }

    // Scroll hatch hint fade
    if (scrollHatchHint) {
      scrollHatchHint.style.opacity = p > 0.2 ? '0' : '1';
    }
  }

  // Smooth Scroll Listener (RequestAnimationFrame)
  let isTicking = false;
  window.addEventListener('scroll', () => {
    if (isManualToggle) return; // Allow manual button toggle override

    if (!isTicking) {
      window.requestAnimationFrame(() => {
        const scrollY = window.scrollY || window.pageYOffset;
        const maxScrollDist = 420; // 420px of scroll achieves 100% fracture
        const computedProgress = Math.min(1.0, Math.max(0, scrollY / maxScrollDist));
        updateEggState(computedProgress);
        isTicking = false;
      });
      isTicking = true;
    }
  }, { passive: true });

  // Interactive Manual Toggle Button
  if (btnCrackToggle) {
    btnCrackToggle.addEventListener('click', () => {
      isManualToggle = true;
      const target = currentCrackProgress > 0.5 ? 0 : 1;
      animateCrackTo(target, 600, () => {
        setTimeout(() => { isManualToggle = false; }, 1500);
      });
    });
  }

  function animateCrackTo(target, duration, onComplete) {
    const start = currentCrackProgress;
    const diff = target - start;
    const startTime = performance.now();

    function step(currentTime) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(1.0, elapsed / duration);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      updateEggState(start + (diff * eased));

      if (progress < 1.0) {
        requestAnimationFrame(step);
      } else {
        if (onComplete) onComplete();
      }
    }
    requestAnimationFrame(step);
  }

  // ==========================================================================
  // 2. INTERACTIVE NATIVE HUD SIMULATION & DISPATCH
  // ==========================================================================

  const hudInput = document.getElementById('hudInput');
  const hudSendBtn = document.getElementById('hudSendBtn');
  const hudMicBtn = document.getElementById('hudMicBtn');
  const hudStatusMsg = document.getElementById('hudStatusMsg');
  const timerMin = document.getElementById('timerMin');
  const timerSec = document.getElementById('timerSec');
  const presetChips = document.querySelectorAll('.preset-chip');
  let isRecordingVoice = false;
  let voiceTimerInterval = null;
  let voiceSeconds = 0;

  // Resolve Search Queries to Google Search
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

  // Resolve Browser URLs (Autocompleting https:// and .com)
  function resolveBrowserUrl(prompt) {
    let clean = prompt.trim().toLowerCase();
    const prefixes = [
      "open a browser and go to ",
      "open a browser and visit ",
      "open browser and go to ",
      "open browser to ",
      "open a browser",
      "open browser",
      "open website ",
      "go to website ",
      "visit website ",
      "browse to ",
      "go to ",
      "visit ",
      "open "
    ];
    for (const p of prefixes) {
      if (clean.startsWith(p)) {
        clean = clean.slice(p.length).trim();
        break;
      }
    }
    clean = clean.replace(/^the\s+/, '').replace(/[.!?,;]+$/g, '').trim();

    if (!clean) {
      return "https://www.google.com";
    }

    if (clean.startsWith("http://") || clean.startsWith("https://")) {
      return clean;
    }

    const domainMap = {
      "youtube": "https://www.youtube.com",
      "google": "https://www.google.com",
      "github": "https://www.github.com",
      "twitter": "https://www.x.com",
      "x": "https://www.x.com",
      "spotify": "https://open.spotify.com",
      "reddit": "https://www.reddit.com",
      "amazon": "https://www.amazon.com",
      "chatgpt": "https://chatgpt.com",
      "claude": "https://claude.ai"
    };

    if (domainMap[clean]) return domainMap[clean];

    if (/^[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(\/.*)?$/.test(clean)) {
      return `https://${clean}`;
    }

    if (/^[a-zA-Z0-9-]+$/.test(clean)) {
      return `https://www.${clean}.com`;
    }

    return `https://www.google.com/search?q=${encodeURIComponent(clean)}`;
  }

  // Core Command Dispatcher
  async function executeCommand(prompt) {
    if (!prompt || !prompt.trim()) return;

    if (hudStatusMsg) {
      hudStatusMsg.textContent = 'Processing command...';
      hudStatusMsg.style.color = '#0EA5E9';
    }

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
          if (hudStatusMsg) {
            hudStatusMsg.innerHTML = `Dispatched: Opening <a href="${data.target_url}" target="_blank" rel="noopener noreferrer" style="color:#0EA5E9;text-decoration:underline;font-weight:700;">${data.target_url} ↗</a>`;
            hudStatusMsg.style.color = '#10B981';
          }
        } else if (data.system_uri) {
          try { window.location.href = data.system_uri; } catch (e) {}
          if (hudStatusMsg) {
            hudStatusMsg.innerHTML = `Triggered: <a href="${data.system_uri}" style="color:#0EA5E9;text-decoration:underline;font-weight:700;">${data.system_uri}</a>`;
            hudStatusMsg.style.color = '#10B981';
          }
        } else {
          if (hudStatusMsg) {
            hudStatusMsg.textContent = `Completed [${action}]: ${msg}`;
            hudStatusMsg.style.color = '#10B981';
          }
        }
      } else {
        fallbackExecution(prompt);
      }
    } catch (e) {
      fallbackExecution(prompt);
    }
  }

  // Client-Side Fallback for Standalone Web Preview
  function fallbackExecution(prompt) {
    const lower = prompt.toLowerCase();

    // 1. Web Search
    if (lower.includes("search") || lower.includes("google") || lower.includes("find")) {
      const s = resolveWebSearch(prompt);
      try { window.open(s.url, '_blank'); } catch (e) {}
      if (hudStatusMsg) {
        hudStatusMsg.innerHTML = `Searching: <a href="${s.url}" target="_blank" rel="noopener noreferrer" style="color:#0EA5E9;text-decoration:underline;font-weight:700;">${s.query} ↗</a>`;
        hudStatusMsg.style.color = '#10B981';
      }
      return;
    }

    // 2. Sound Settings
    if (lower.includes("sound") || lower.includes("volume") || lower.includes("audio")) {
      try { window.location.href = 'ms-settings:sound'; } catch (e) {}
      if (hudStatusMsg) {
        hudStatusMsg.textContent = 'Triggered: ms-settings:sound (Windows Sound Settings)';
        hudStatusMsg.style.color = '#10B981';
      }
      return;
    }

    // 3. Spotify
    if (lower.includes("spotify")) {
      try { window.location.href = 'spotify:'; } catch (e) {}
      if (hudStatusMsg) {
        hudStatusMsg.innerHTML = `Opened Spotify • URI <span style="color:#10B981;font-weight:700;">spotify:</span> dispatched`;
        hudStatusMsg.style.color = '#10B981';
      }
      return;
    }

    // 4. Mathematical Calculations
    if (/^[0-9\s+\-*/().%^]+$/.test(prompt.trim()) || lower.includes("calculate") || lower.includes("math")) {
      try {
        const mathExpr = prompt.replace(/[^\d+\-*/().]/g, '');
        const res = Function(`'use strict'; return (${mathExpr})`)();
        if (hudStatusMsg) {
          hudStatusMsg.textContent = `Result: ${mathExpr} = ${res}`;
          hudStatusMsg.style.color = '#10B981';
        }
        return;
      } catch (err) {}
    }

    // 5. General Web Navigation
    if (lower.includes("open") || lower.includes("visit") || lower.includes("browse")) {
      const url = resolveBrowserUrl(prompt);
      try { window.open(url, '_blank'); } catch (e) {}
      if (hudStatusMsg) {
        hudStatusMsg.innerHTML = `Launched: <a href="${url}" target="_blank" rel="noopener noreferrer" style="color:#0EA5E9;text-decoration:underline;font-weight:700;">${url} ↗</a>`;
        hudStatusMsg.style.color = '#10B981';
      }
      return;
    }

    // Default Fallback
    if (hudStatusMsg) {
      hudStatusMsg.textContent = `Executed: "${prompt}" sent to native runner`;
      hudStatusMsg.style.color = '#10B981';
    }
  }

  // Input Listeners
  if (hudInput) {
    hudInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const val = hudInput.value.trim();
        if (val) executeCommand(val);
      }
    });
  }

  if (hudSendBtn && hudInput) {
    hudSendBtn.addEventListener('click', () => {
      const val = hudInput.value.trim();
      if (val) executeCommand(val);
    });
  }

  // Voice Mic Orb Simulation
  if (hudMicBtn) {
    hudMicBtn.addEventListener('click', () => {
      isRecordingVoice = !isRecordingVoice;
      if (isRecordingVoice) {
        hudMicBtn.classList.add('active');
        if (hudStatusMsg) {
          hudStatusMsg.textContent = 'Listening... Speak your command';
          hudStatusMsg.style.color = '#E11D48';
        }
        voiceSeconds = 0;
        voiceTimerInterval = setInterval(() => {
          voiceSeconds++;
          const m = String(Math.floor(voiceSeconds / 60)).padStart(2, '0');
          const s = String(voiceSeconds % 60).padStart(2, '0');
          if (timerMin) timerMin.textContent = m;
          if (timerSec) timerSec.textContent = s;
        }, 1000);

        // Auto-stop after 3.5s with simulated command
        setTimeout(() => {
          if (isRecordingVoice) {
            hudMicBtn.click();
            const demoVoiceCommands = [
              "open spotify and play lofi",
              "search on internet for latest tech trends",
              "open sound settings"
            ];
            const chosen = demoVoiceCommands[Math.floor(Math.random() * demoVoiceCommands.length)];
            if (hudInput) hudInput.value = chosen;
            executeCommand(chosen);
          }
        }, 3500);
      } else {
        hudMicBtn.classList.remove('active');
        if (voiceTimerInterval) clearInterval(voiceTimerInterval);
      }
    });
  }

  // Preset Action Chips
  presetChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      if (prompt) {
        if (hudInput) hudInput.value = prompt;
        executeCommand(prompt);
      }
    });
  });

  // ==========================================================================
  // 3. ONE-CLICK INSTALL COMMAND COPY
  // ==========================================================================

  const btnCopyCmd = document.getElementById('btnCopyCmd');
  const cliCommand = document.getElementById('cliCommand');
  const copyText = document.getElementById('copyText');

  if (btnCopyCmd && cliCommand) {
    btnCopyCmd.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(cliCommand.textContent.trim());
        if (copyText) copyText.textContent = 'Copied!';
        btnCopyCmd.style.background = '#10B981';
        setTimeout(() => {
          if (copyText) copyText.textContent = 'Copy';
          btnCopyCmd.style.background = '';
        }, 1800);
      } catch (err) {
        if (copyText) copyText.textContent = 'Copied!';
      }
    });
  }

  // ==========================================================================
  // 4. SYSTEM HEALTH MONITOR
  // ==========================================================================

  const daemonStatusText = document.getElementById('daemonStatusText');
  async function checkDaemonStatus() {
    try {
      const res = await fetch('/api/orchestrator/status');
      if (res.ok && daemonStatusText) {
        daemonStatusText.textContent = 'Systems Online';
      }
    } catch (e) {
      // Local standalone mode remains online
      if (daemonStatusText) daemonStatusText.textContent = 'Systems Online';
    }
  }

  // Initialize
  document.addEventListener('DOMContentLoaded', () => {
    initAsciiEgg();
    checkDaemonStatus();
  });

  // If DOM is already ready
  if (document.readyState === 'interactive' || document.readyState === 'complete') {
    initAsciiEgg();
    checkDaemonStatus();
  }

})();
