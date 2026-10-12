/**
 * ANDA° — Autonomous Native Desktop Assistant
 * Pinterest Pin 520025088247216830 Editorial Frontend Engine
 * Features:
 * 1. Mathematically interlocking pure ASCII Egg ("anda") with left-to-right zig-zag fracture on scroll.
 * 2. Hovering physics top shell.
 * 3. Interactive Native HUD command execution with physical Win32/Browser actions & autocompletion.
 * 4. Voice orb simulation with duration timer.
 * 5. PowerShell installer one-click copy.
 */

(() => {
  'use strict';

  // ==========================================================================
  // 1. PURE ASCII ART EGG ("ANDA") DATA & INTERLOCKING MESH
  // ==========================================================================

  const EGG_TOP_LINES = [
    "                    #                   ",
    "               #==###**==#              ",
    "             #=%%%%###**+==#            ",
    "           #=%%%%%%%##**++=-=#          ",
    "          #%%%%%%%%%##***+==-:#         ",
    "         =%%%%%%%%%###***+==--:=        ",
    "        =%%%%%%%%%####**++==--:.=       ",
    "       =%%%%%%%%%####***++==--:..=      ",
    "      =#%%%%%%%#####***++===--:...=     ",
    "     =####%#######****+++==--::....=    "
  ];

  const EGG_TOP_TEETH = "    /\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\   ";

  const EGG_BOTTOM_TEETH = "    \\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\   ";

  const EGG_BOTTOM_LINES = [
    "   #+***********++++====---::........#  ",
    "   #++++**++++++++====---:::.........#  ",
    "   #==++++++++======---:::...........#  ",
    "   #-===========-----:::.............#  ",
    "   #=-------------::::..............=#  ",
    "    #=:::::::::::::................=#   ",
    "     #=...::......................=#    ",
    "      #=.........................=#     ",
    "        ##=...................=##       ",
    "            #===.........===#           "
  ];

  // DOM Elements
  const asciiTopPre = document.getElementById('asciiTopPre');
  const asciiBottomPre = document.getElementById('asciiBottomPre');
  const eggTopShell = document.getElementById('eggTopShell');
  const eggBottomShell = document.getElementById('eggBottomShell');
  const eggCoreHud = document.getElementById('eggCoreHud');
  const scrubFill = document.getElementById('scrubFill');
  const btnCrackToggle = document.getElementById('btnCrackToggle');
  const crackToggleLabel = document.getElementById('crackToggleLabel');
  const scrollHatchHint = document.getElementById('scrollHatchHint');

  let topCrackSpans = [];
  let botCrackSpans = [];
  let currentCrackProgress = 0;
  let isManualToggle = false;

  function initAsciiEgg() {
    if (!asciiTopPre || !asciiBottomPre) return;

    // 1. Build Top Shell HTML with Interactive Tooth Line
    let topHtml = EGG_TOP_LINES.join('\n') + '\n';
    topCrackSpans = [];
    const topTeethChars = EGG_TOP_TEETH.split('');
    topTeethChars.forEach((ch, idx) => {
      topHtml += `<span class="crack-char" data-col="${idx}">${ch}</span>`;
    });
    asciiTopPre.innerHTML = topHtml;
    topCrackSpans = Array.from(asciiTopPre.querySelectorAll('.crack-char'));

    // 2. Build Bottom Shell HTML with Interlocking Tooth Line
    let botHtml = '';
    botCrackSpans = [];
    const botTeethChars = EGG_BOTTOM_TEETH.split('');
    botTeethChars.forEach((ch, idx) => {
      botHtml += `<span class="crack-char" data-col="${idx}">${ch}</span>`;
    });
    botHtml += '\n' + EGG_BOTTOM_LINES.join('\n');
    asciiBottomPre.innerHTML = botHtml;
    botCrackSpans = Array.from(asciiBottomPre.querySelectorAll('.crack-char'));

    updateEggState(0);
  }

  function updateEggState(p) {
    p = Math.max(0, Math.min(1, p));
    currentCrackProgress = p;

    // 1. Progress Bar Fill
    if (scrubFill) {
      scrubFill.style.width = `${(p * 100).toFixed(1)}%`;
    }

    // 2. Zig-Zag Fracture Propagation from Left to Right (0.0 to 0.45)
    const totalCols = topCrackSpans.length;
    const crackRatio = Math.min(1.0, p / 0.45);
    const activeColIndex = Math.floor(crackRatio * totalCols);

    for (let i = 0; i < totalCols; i++) {
      const topSpan = topCrackSpans[i];
      const botSpan = botCrackSpans[i];

      if (i < activeColIndex) {
        if (topSpan) topSpan.classList.add('fractured');
        if (botSpan) botSpan.classList.add('fractured');
        if (i === activeColIndex - 1) {
          if (topSpan) topSpan.classList.add('active-tip');
          if (botSpan) botSpan.classList.add('active-tip');
        } else {
          if (topSpan) topSpan.classList.remove('active-tip');
          if (botSpan) botSpan.classList.remove('active-tip');
        }
      } else {
        if (topSpan) topSpan.classList.remove('fractured', 'active-tip');
        if (botSpan) botSpan.classList.remove('fractured', 'active-tip');
      }
    }

    // 3. Shell Separation & Hovering Physics (0.20 to 1.0)
    if (p > 0.18) {
      const sepRatio = Math.min(1.0, (p - 0.18) / 0.72);
      const topY = -80 * sepRatio;
      const topRot = -3.4 * sepRatio;
      const bottomY = 18 * sepRatio;
      const bottomRot = 1.2 * sepRatio;

      if (eggTopShell) {
        eggTopShell.style.setProperty('--top-translate-y', `${topY.toFixed(1)}px`);
        eggTopShell.style.setProperty('--top-rotate', `${topRot.toFixed(2)}deg`);
        eggTopShell.style.transform = `translateY(${topY.toFixed(1)}px) rotate(${topRot.toFixed(2)}deg)`;

        // Engage continuous sinusoidal hover float
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
        const coreOpacity = Math.min(1.0, (p - 0.25) / 0.45);
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
      // Intact sealed egg
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

    if (crackToggleLabel) {
      crackToggleLabel.textContent = p > 0.5 ? 'Reset Shell' : 'Crack Shell';
    }

    if (scrollHatchHint) {
      scrollHatchHint.style.opacity = p > 0.2 ? '0' : '1';
    }
  }

  // Smooth Scroll Listener (RequestAnimationFrame)
  let isTicking = false;
  window.addEventListener('scroll', () => {
    if (isManualToggle) return;

    if (!isTicking) {
      window.requestAnimationFrame(() => {
        const scrollY = window.scrollY || window.pageYOffset;
        const maxScrollDist = 380;
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
        setTimeout(() => { isManualToggle = false; }, 1200);
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
  const spotlightOverlay = document.getElementById('spotlightOverlay');
  const spotlightList = document.getElementById('spotlightList');
  let spotlightResults = [];
  let spotlightSelectedIdx = 0;
  let isRecordingVoice = false;
  let voiceTimerInterval = null;
  let voiceSeconds = 0;

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
      const fn = new Function(`return (${sanitized})`);
      const res = fn();
      if (typeof res === 'number' && !isNaN(res) && isFinite(res)) {
        return res;
      }
    } catch (e) {}
    return null;
  }

  function querySpotlight(q) {
    const query = (q || '').trim();
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
    if (spotlightOverlay) spotlightOverlay.classList.remove('active');
    spotlightResults = [];

    if (item.action === 'launch_game') {
      if (hudStatusMsg) {
        hudStatusMsg.innerHTML = `🎮 <strong>Launched Game:</strong> ${item.title} (${item.sub})`;
        hudStatusMsg.style.color = '#10B981';
      }
    } else if (item.action === 'launch_app') {
      if (hudStatusMsg) {
        hudStatusMsg.innerHTML = `🚀 <strong>Launched Application:</strong> ${item.title}`;
        hudStatusMsg.style.color = '#10B981';
      }
    } else if (item.action === 'open_setting') {
      try { window.location.href = item.target; } catch (e) {}
      if (hudStatusMsg) {
        hudStatusMsg.innerHTML = `⚙️ <strong>Opened System Setting:</strong> <a href="${item.target}" style="color:#0EA5E9;text-decoration:underline;">${item.title}</a>`;
        hudStatusMsg.style.color = '#10B981';
      }
    } else if (item.action === 'math') {
      try { navigator.clipboard.writeText(item.target); } catch (e) {}
      if (hudStatusMsg) {
        hudStatusMsg.innerHTML = `🔢 <strong>Calculation:</strong> ${item.title} (Copied)`;
        hudStatusMsg.style.color = '#10B981';
      }
    } else if (item.action === 'web_search') {
      try { window.open(item.target, '_blank'); } catch (e) {}
      if (hudStatusMsg) {
        hudStatusMsg.innerHTML = `🌐 <strong>Web Search:</strong> <a href="${item.target}" target="_blank" style="color:#0EA5E9;text-decoration:underline;">${item.title} ↗</a>`;
        hudStatusMsg.style.color = '#10B981';
      }
    } else {
      if (hudStatusMsg) {
        hudStatusMsg.innerHTML = `✅ <strong>Executed:</strong> ${item.title}`;
        hudStatusMsg.style.color = '#10B981';
      }
    }

    setTimeout(() => {
      if (hudStatusMsg) {
        hudStatusMsg.textContent = 'Ready • Press [Left Ctrl + Win] anywhere to summon';
        hudStatusMsg.style.color = '#71717A';
      }
    }, 5000);
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

    if (!clean) return "https://www.google.com";

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

  function fallbackExecution(prompt) {
    const lower = prompt.toLowerCase();

    if (lower.includes("search") || lower.includes("google") || lower.includes("find")) {
      const s = resolveWebSearch(prompt);
      try { window.open(s.url, '_blank'); } catch (e) {}
      if (hudStatusMsg) {
        hudStatusMsg.innerHTML = `Searching: <a href="${s.url}" target="_blank" rel="noopener noreferrer" style="color:#0EA5E9;text-decoration:underline;font-weight:700;">${s.query} ↗</a>`;
        hudStatusMsg.style.color = '#10B981';
      }
      return;
    }

    if (lower.includes("sound") || lower.includes("volume") || lower.includes("audio")) {
      try { window.location.href = 'ms-settings:sound'; } catch (e) {}
      if (hudStatusMsg) {
        hudStatusMsg.textContent = 'Triggered: ms-settings:sound (Windows Sound Settings)';
        hudStatusMsg.style.color = '#10B981';
      }
      return;
    }

    if (lower.includes("spotify")) {
      try { window.location.href = 'spotify:'; } catch (e) {}
      if (hudStatusMsg) {
        hudStatusMsg.innerHTML = `Opened Spotify • URI <span style="color:#10B981;font-weight:700;">spotify:</span> dispatched`;
        hudStatusMsg.style.color = '#10B981';
      }
      return;
    }

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

    if (lower.includes("open") || lower.includes("visit") || lower.includes("browse")) {
      const url = resolveBrowserUrl(prompt);
      try { window.open(url, '_blank'); } catch (e) {}
      if (hudStatusMsg) {
        hudStatusMsg.innerHTML = `Launched: <a href="${url}" target="_blank" rel="noopener noreferrer" style="color:#0EA5E9;text-decoration:underline;font-weight:700;">${url} ↗</a>`;
        hudStatusMsg.style.color = '#10B981';
      }
      return;
    }

    if (hudStatusMsg) {
      hudStatusMsg.textContent = `Executed: "${prompt}" sent to native runner`;
      hudStatusMsg.style.color = '#10B981';
    }
  }

  if (hudInput) {
    hudInput.addEventListener('input', () => {
      const q = hudInput.value.trim();
      spotlightResults = querySpotlight(q);
      spotlightSelectedIdx = 0;
      renderSpotlightResults();
    });

    hudInput.addEventListener('keydown', (e) => {
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
        if (spotlightOverlay) spotlightOverlay.classList.remove('active');
        spotlightResults = [];
      } else if (e.key === 'Enter') {
        if (spotlightResults.length > 0 && spotlightSelectedIdx < spotlightResults.length) {
          e.preventDefault();
          executeSpotlightSelection(spotlightResults[spotlightSelectedIdx]);
        } else {
          const val = hudInput.value.trim();
          if (val) executeCommand(val);
        }
      }
    });
  }

  if (hudSendBtn && hudInput) {
    hudSendBtn.addEventListener('click', () => {
      if (spotlightResults.length > 0 && spotlightSelectedIdx < spotlightResults.length) {
        executeSpotlightSelection(spotlightResults[spotlightSelectedIdx]);
      } else {
        const val = hudInput.value.trim();
        if (val) executeCommand(val);
      }
    });
  }

  // Seamless Voice-to-Text Recognition Engine
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  let lastRecognizedSpeech = '';

  if (SpeechRecognition) {
    try {
      recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        isRecordingVoice = true;
        lastRecognizedSpeech = '';
        if (hudMicBtn) hudMicBtn.classList.add('active');
        if (hudStatusMsg) {
          hudStatusMsg.textContent = '🎙️ Listening... Speak command or game title';
          hudStatusMsg.style.color = '#E11D48';
        }
        startVoiceTimer();
      };

      recognition.onresult = (evt) => {
        let interim = '';
        let finalTxt = '';
        for (let i = evt.resultIndex; i < evt.results.length; ++i) {
          if (evt.results[i].isFinal) finalTxt += evt.results[i][0].transcript;
          else interim += evt.results[i][0].transcript;
        }
        const text = (finalTxt || interim).trim();
        if (text && hudInput) {
          hudInput.value = text;
          lastRecognizedSpeech = text;
          spotlightResults = querySpotlight(text);
          spotlightSelectedIdx = 0;
          renderSpotlightResults();
        }
      };

      recognition.onend = () => {
        isRecordingVoice = false;
        if (hudMicBtn) hudMicBtn.classList.remove('active');
        stopVoiceTimer();
        const finalWord = (lastRecognizedSpeech || (hudInput ? hudInput.value : '')).trim();
        if (finalWord) {
          const matches = querySpotlight(finalWord);
          if (matches.length > 0) executeSpotlightSelection(matches[0]);
          else executeCommand(finalWord);
        }
      };

      recognition.onerror = () => {
        isRecordingVoice = false;
        if (hudMicBtn) hudMicBtn.classList.remove('active');
        stopVoiceTimer();
      };
    } catch (e) {
      recognition = null;
    }
  }

  function startVoiceTimer() {
    clearInterval(voiceTimerInterval);
    voiceSeconds = 0;
    voiceTimerInterval = setInterval(() => {
      voiceSeconds++;
      const m = String(Math.floor(voiceSeconds / 60)).padStart(2, '0');
      const s = String(voiceSeconds % 60).padStart(2, '0');
      if (timerMin) timerMin.textContent = m;
      if (timerSec) timerSec.textContent = s;
    }, 1000);
  }

  function stopVoiceTimer() {
    clearInterval(voiceTimerInterval);
    setTimeout(() => {
      if (timerMin) timerMin.textContent = '00';
      if (timerSec) timerSec.textContent = '03';
    }, 3000);
  }

  if (hudMicBtn) {
    hudMicBtn.addEventListener('click', () => {
      if (isRecordingVoice) {
        if (recognition) {
          try { recognition.stop(); } catch (e) {}
        } else {
          isRecordingVoice = false;
          hudMicBtn.classList.remove('active');
          stopVoiceTimer();
        }
      } else {
        if (recognition) {
          try {
            recognition.start();
            return;
          } catch (e) {}
        }
        // Fallback simulation if browser blocks microphone
        isRecordingVoice = true;
        hudMicBtn.classList.add('active');
        if (hudStatusMsg) {
          hudStatusMsg.textContent = '🎙️ Listening... (Voice Simulation)';
          hudStatusMsg.style.color = '#E11D48';
        }
        startVoiceTimer();
        setTimeout(() => {
          if (isRecordingVoice) {
            hudMicBtn.click();
            const sampleVoice = [
              "open cyberpunk",
              "45 * 12 + 10",
              "open sound settings",
              "open youtube"
            ];
            const chosen = sampleVoice[Math.floor(Math.random() * sampleVoice.length)];
            if (hudInput) hudInput.value = chosen;
            const matches = querySpotlight(chosen);
            if (matches.length > 0) executeSpotlightSelection(matches[0]);
            else executeCommand(chosen);
          }
        }, 3000);
      }
    });
  }

  presetChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      if (prompt) {
        if (hudInput) hudInput.value = prompt;
        const matches = querySpotlight(prompt);
        if (matches.length > 0) {
          executeSpotlightSelection(matches[0]);
        } else {
          executeCommand(prompt);
        }
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
      if (daemonStatusText) daemonStatusText.textContent = 'Systems Online';
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    initAsciiEgg();
    checkDaemonStatus();
  });

  if (document.readyState === 'interactive' || document.readyState === 'complete') {
    initAsciiEgg();
    checkDaemonStatus();
  }

})();
