(() => {
  'use strict';

  const commands = {
    windows: 'irm https://raw.githubusercontent.com/PTejasKr/ANDA/main/install.ps1 | iex',
    local: 'cd /d D:\\mlh && install.cmd',
  };

  const commandEl = document.getElementById('installCommand');
  const copyButton = document.getElementById('copyCommand');
  const copyStatus = document.getElementById('copyStatus');
  const tabs = Array.from(document.querySelectorAll('.tab'));

  function setCommand(key) {
    commandEl.textContent = commands[key];
    tabs.forEach((tab) => {
      tab.classList.toggle('active', tab.dataset.command === key);
    });
    copyStatus.textContent = key === 'windows'
      ? 'Creates laptop shortcuts, starts the local stack, and opens this installer page.'
      : 'Runs the installer from this checkout without downloading a fresh copy.';
  }

  tabs.forEach((tab) => {
    tab.addEventListener('click', () => setCommand(tab.dataset.command));
  });

  copyButton.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(commandEl.textContent);
      copyButton.textContent = 'Copied';
      setTimeout(() => {
        copyButton.textContent = 'Copy';
      }, 1400);
    } catch (error) {
      copyStatus.textContent = commandEl.textContent;
    }
  });

  const statusEls = {
    orchestrator: document.getElementById('orchestratorStatus'),
    worker: document.getElementById('workerStatus'),
    daemon: document.getElementById('daemonStatus'),
  };
  const rows = {
    orchestrator: document.querySelector('[data-service="orchestrator"]'),
    worker: document.querySelector('[data-service="worker"]'),
    daemon: document.querySelector('[data-service="daemon"]'),
  };
  const stackStatus = document.getElementById('stackStatus');
  const stackMeter = document.getElementById('stackMeter');

  function setService(name, isOnline) {
    statusEls[name].textContent = isOnline ? 'Online' : 'Offline';
    rows[name].classList.toggle('online', isOnline);
    rows[name].classList.toggle('offline', !isOnline);
  }

  async function probe(url, parser = 'json') {
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(1300) });
      if (!response.ok) return null;
      return parser === 'json' ? response.json() : response.text();
    } catch (error) {
      return null;
    }
  }

  async function refreshStatus() {
    const system = await probe('/api/system/status');
    const worker = await probe('http://localhost:50051/health');
    const daemon = await probe('http://localhost:8081/health');

    const orchestratorOnline = Boolean(system && system.orchestrator === 'online');
    const workerOnline = Boolean(worker && worker.status === 'healthy');
    const daemonOnline = Boolean(daemon && daemon.status === 'active');

    setService('orchestrator', orchestratorOnline);
    setService('worker', workerOnline);
    setService('daemon', daemonOnline);

    const onlineCount = [orchestratorOnline, workerOnline, daemonOnline].filter(Boolean).length;
    stackMeter.style.width = `${(onlineCount / 3) * 100}%`;
    stackStatus.textContent = onlineCount === 3 ? 'Ready' : onlineCount > 0 ? 'Partial' : 'Offline';
  }

  refreshStatus();
  setInterval(refreshStatus, 5000);
})();
