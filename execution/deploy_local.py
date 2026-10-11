"""
Local Deployment & Health Orchestration Script
Spawns the dual-plane stack (Elevated Daemon, Python Worker, Go Orchestrator)
and verifies live operational status at the local level.
"""

import os
import subprocess
import sys
import time
import requests


def start_stack(with_hotkey: bool = False):
    print("\n" + "="*70)
    print("[*] DEPLOYING OMNI-OPERATOR OS AGENT (LOCAL LEVEL)")
    print("="*70)

    # 1. Start Elevated Daemon
    daemon_env = os.environ.copy()
    daemon_env["DAEMON_PIPE"] = r"\\.\pipe\omni_daemon_ipc"
    daemon_env["DAEMON_HTTP_PORT"] = "8081"
    print("[1/3] Spawning Elevated Daemon (Named Pipe: \\\\.\\pipe\\omni_daemon_ipc)...")
    daemon_proc = subprocess.Popen([os.path.abspath("daemon.exe")], env=daemon_env)

    # 2. Start Python Worker Plane
    worker_env = os.environ.copy()
    worker_env["WORKER_PORT"] = "50051"
    print("[2/3] Spawning Unprivileged Worker Plane on port 50051...")
    worker_proc = subprocess.Popen(
        [sys.executable, os.path.abspath("backend/worker/worker_api.py")],
        env=worker_env,
    )

    # 3. Start Go Orchestrator
    orch_env = os.environ.copy()
    orch_env["ORCHESTRATOR_PORT"] = "8080"
    orch_env["WORKER_HOST"] = "http://127.0.0.1:50051"
    orch_env["STORAGE_ROOT"] = "storage"
    print("[3/3] Spawning Go Orchestrator on port 8080 (UI & File Manager)...")
    orch_proc = subprocess.Popen([os.path.abspath("orchestrator.exe")], env=orch_env)

    procs = [daemon_proc, worker_proc, orch_proc]

    # Optional: Start Global Hotkey Listener
    if with_hotkey:
        print("[+] Spawning Windows Global Hotkey Listener [Ctrl + Win + Space]...")
        hotkey_proc = subprocess.Popen([sys.executable, os.path.abspath("execution/global_hotkey_listener.py")])
        procs.append(hotkey_proc)

    # Wait for services to initialize
    print("\n[*] Waiting for services to become responsive...")
    time.sleep(2.0)

    # Health Checks
    try:
        # Check Orchestrator & Static Frontend
        r_ui = requests.get("http://127.0.0.1:8080/", timeout=3)
        print(f"[+] Frontend UI Check: HTTP {r_ui.status_code} ({len(r_ui.content)} bytes)")
        assert r_ui.status_code == 200, "Frontend index.html failed to serve"

        # Check Unified System Status
        r_sys = requests.get("http://127.0.0.1:8080/api/system/status", timeout=3)
        sys_data = r_sys.json()
        print(f"[+] Subsystem Status Check: {sys_data}")
        assert sys_data["orchestrator"] == "online"
        assert sys_data["worker_plane"] == "online"
        assert sys_data["daemon_ipc"] == "online"

        # Check File Manager API
        r_fs = requests.get("http://127.0.0.1:8080/api/fs/list?folder=ingest", timeout=3)
        print(f"[+] File Manager Ingest Queue Check: HTTP {r_fs.status_code} ({len(r_fs.json())} items)")
        assert r_fs.status_code == 200

        # Check Worker Direct Endpoint
        r_worker = requests.get("http://127.0.0.1:50051/health", timeout=3)
        print(f"[+] Worker Health Check: {r_worker.json()}")
        assert r_worker.status_code == 200

        # Check Daemon Direct Endpoint
        r_daemon = requests.get("http://127.0.0.1:8081/health", timeout=3)
        print(f"[+] Daemon Health Check: {r_daemon.json()}")
        assert r_daemon.status_code == 200

        print("\n" + "="*70)
        print(">>> LOCAL DEPLOYMENT VERIFIED: ALL SUBSYSTEMS FULLY OPERATIONAL <<<")
        print("  - File Manager UI : http://localhost:8080/")
        print("  - Orchestrator API: http://localhost:8080/api/system/status")
        print("  - Worker Plane    : http://localhost:50051/health")
        print("  - Daemon Admin    : http://localhost:8081/health")
        print("="*70 + "\n")
        return procs

    except Exception as e:
        print(f"[!] Health check failed: {e}")
        for p in procs:
            try:
                p.terminate()
                p.wait(timeout=1.0)
            except Exception:
                pass
        raise


if __name__ == "__main__":
    with_hotkey = "--with-hotkey" in sys.argv
    procs = start_stack(with_hotkey=with_hotkey)
    # Keep running or exit cleanly if run in batch mode
    if "--verify-only" in sys.argv:
        print("[*] Verification mode complete. Stopping services...")
        for p in procs:
            p.terminate()
            p.wait()
    else:
        try:
            print("[*] Stack running. Press Ctrl+C to terminate.")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[*] Shutting down local services...")
            for p in procs:
                p.terminate()
                p.wait()
            print("[+] Graceful shutdown complete.")
