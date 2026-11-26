<div align="center">

# 🤖 ANDA
### Autonomous Desktop Butler & System Automation Daemon

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge" alt="License" /></a>
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Go-Microservice-00ADD8?style=for-the-badge&logo=go&logoColor=white" alt="Go" />
  <img src="https://img.shields.io/badge/Docker-Containerized-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/Cloudflare-Edge%20Workers-F38020?style=for-the-badge&logo=cloudflare&logoColor=white" alt="Cloudflare" />
</p>

```
  A local system intelligence daemon and cross-platform automation assistant
  engineered for desktop orchestration, IPC task scheduling, and secure edge proxying.
```

---

</div>

## 📑 Table of Contents

- [Overview](#-overview)
- [Architecture Blueprint](#-architecture-blueprint)
- [Core Features](#-core-features)
- [Directory Structure](#-directory-structure)
- [Quick Start](#-quick-start)
- [Security Audit & Hardening](#-security-audit--hardening)
- [License](#-license)

---

## 🌟 Overview

**ANDA** acts as an autonomous, low-overhead digital butler running on user machines. Designed with a decoupled architecture, ANDA bridges OS-level event listeners (global hotkeys, audio triggers, process monitoring) with background execution workers and external cloud integrations.

---

## 🏗️ Architecture Blueprint

```
┌────────────────────────────────────────────────────────────────────────┐
│                        User Interaction Tier                           │
│     [ Global Hotkey Listener ]  ◄──►  [ Desktop System Tray ]         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ IPC (Sockets / Named Pipes)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     ANDA Core Server (Python/Go)                       │
│  ├── Intent Parser & Router (Directives Engine)                        │
│  ├── Asynchronous Task Scheduler                                      │
│  └── Local Storage & SQLite State Store                                │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Secure Edge Tunnel
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                  Edge Integration & Proxies                            │
│     [ Cloudflare Workers ]  ◄──►  [ Fly.io Microservices ]            │
└────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Core Features

* **Global Hotkey Daemon (`hotkey_daemon.py`):** Low-latency native input hook for triggering instant commands and automated workflows.
* **Dual Runtime Pipeline:** Heavy automation pipelines orchestrated in Python, with performance-critical edge proxying in Go.
* **Deterministic Directives:** Layered execution system separating business intent (`directives/`) from execution scripts (`execution/`).
* **Containerized Deployment:** Ready for local execution, Docker containers, or distributed Fly.io deployment.

---

## 📂 Directory Structure

```bash
ANDA/
├── backend/               # Core backend services and API routers
├── frontend/              # Minimal dashboard for task logs and diagnostics
├── cloudflare/            # Edge proxy scripts and routing rules
├── directives/            # Standard operating procedures and agent prompts
├── execution/             # Deterministic Python scripts and task runners
├── storage/               # Local SQLite database and cached assets
├── hotkey_daemon.py       # Background native hotkey listener
├── server.py              # Main local API service
├── docker-compose.yml     # Multi-service local orchestrator
└── Dockerfile             # Production container definition
```

---

## 💻 Quick Start

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/PTejasKr/ANDA.git
cd ANDA

# Setup Python virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Launch Local Server & Daemon
```bash
# On Windows:
.\start.bat

# On Linux/macOS:
chmod +x start.sh
./start.sh
```

---

## 🛡️ Security Audit & Hardening

1. **Loopback Binding Isolation:** The local HTTP/RPC server (`server.py`) MUST bind strictly to `127.0.0.1` rather than `0.0.0.0` to prevent unauthorized requests from other devices on local networks.
2. **IPC Token Authentication:** All inter-process communication between `hotkey_daemon.py` and `server.py` should require a locally generated session token passed via request headers.
3. **Environment Security:** Sensitive tokens and cloud credentials should reside in a strictly git-ignored `.env` file.

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.
