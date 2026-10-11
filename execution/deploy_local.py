"""
Local Deployment & Health Orchestration Script
Spawns the dual-plane stack (Elevated Daemon, Python Worker, Go Orchestrator)
and verifies live operational status at the local level.
Handles pre-flight port cleanup, missing binary compilation, and health retry polling.
"""

import os
import subprocess
import sys
import time
import requests


def free_ports(ports=(8080, 50051, 8081)):
    """Terminates stale processes occupying target ports on Windows."""
    if sys.platform != "win32":
        return
    for port in ports:
        try:
            ps_cmd = f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique"
            out = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps_cmd], text=True).strip()
            if out:
                for line in out.splitlines():
                    pid_str = line.strip()
                    if pid_str.isdigit():
                        pid = int(pid_str)
                        if pid > 0 and pid != os.getpid():
                            print(f"[*] Port {port} conflict detected. Terminating PID {pid}...")
                            subprocess.run(["powershell", "-NoProfile", "-Command", f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue"])
        except Exception as e:
            pass
    time.sleep(1.0)


def ensure_binaries():
    """Compiles Go orchestrator and daemon if missing."""
    env = os.environ.copy()
    if sys.platform == "win32":
        os.makedirs("d:\\tmp", exist_ok=True)
        env["GOTMPDIR"] = "d:\\tmp"
        env["TEMP"] = "d:\\tmp"
        env["TMP"] = "d:\\tmp"

    if not os.path.exists("daemon.exe"):
        print("[*] Compiling daemon.exe...")
        subprocess.run(["go", "build", "-o", "daemon.exe", "./backend/daemon"], env=env, check=True)

    if not os.path.exists("orchestrator.exe"):
        print("[*] Compiling orchestrator.exe...")
        subprocess.run(["go", "build", "-o", "orchestrator.exe", "./backend/orchestrator"], env=env, check=True)


def start_stack(with_hotkey: bool = False):
    print("\n" + "="*70)
    print("[*] DEPLOYING ANDA OS AGENT (LOCAL LEVEL)")
    print("="*70)

    # 0. Pre-flight Port Cleanup & Binary Check
    free_ports((8080, 50051, 8081))
    ensure_binaries()

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

    # Optional: Start Native Desktop HUD App
    if with_hotkey:
        print("[+] Spawning ANDA Native Desktop HUD App [Left Ctrl + Win]...")
        if os.path.exists("anda.exe"):
            hud_proc = subprocess.Popen([os.path.abspath("anda.exe")])
            procs.append(hud_proc)
        elif os.path.exists("execution/anda_app.py"):
            hud_proc = subprocess.Popen([sys.executable, os.path.abspath("execution/anda_app.py")])
            procs.append(hud_proc)

    # Poll until services become responsive
    print("\n[*] Waiting for services to become responsive...")
    max_wait = 18.0
    start_time = time.time()
    last_err = None

    while time.time() - start_time < max_wait:
        # Check if any process terminated prematurely
        if daemon_proc.poll() is not None:
            raise RuntimeError(f"Elevated Daemon exited prematurely (code {daemon_proc.returncode})")
        if worker_proc.poll() is not None:
            raise RuntimeError(f"Python Worker exited prematurely (code {worker_proc.returncode})")
        if orch_proc.poll() is not None:
            raise RuntimeError(f"Go Orchestrator exited prematurely (code {orch_proc.returncode})")

        try:
            r_ui = requests.get("http://127.0.0.1:8080/", timeout=1.0)
            r_sys = requests.get("http://127.0.0.1:8080/api/system/status", timeout=1.0)
            r_worker = requests.get("http://127.0.0.1:50051/health", timeout=1.0)
            r_daemon = requests.get("http://127.0.0.1:8081/health", timeout=1.0)

            if (r_ui.status_code == 200 and
                r_sys.status_code == 200 and
                r_worker.status_code == 200 and
                r_daemon.status_code == 200):
                try:
                    sys_data = r_sys.json()
                    worker_data = r_worker.json()
                    daemon_data = r_daemon.json()
                    if sys_data.get("worker_plane") == "online" and sys_data.get("daemon_ipc") == "online":
                        print(f"[+] Frontend Showcase Check: HTTP {r_ui.status_code} ({len(r_ui.content)} bytes)")
                        print(f"[+] Subsystem Status Check: {sys_data}")
                        print(f"[+] Worker Health Check: {worker_data}")
                        print(f"[+] Daemon Health Check: {daemon_data}")
                        last_err = None
                        break
                except Exception as parse_e:
                    last_err = parse_e
        except Exception as e:
            last_err = e

        time.sleep(0.5)

    if last_err is not None:
        print(f"[!] Health check timeout reached. Last error: {last_err}")
        for p in procs:
            try:
                p.terminate()
                p.wait(timeout=1.0)
            except Exception:
                pass
        raise last_err

    # Check File Manager API
    try:
        r_fs = requests.get("http://127.0.0.1:8080/api/fs/list?folder=ingest", timeout=3)
        print(f"[+] File Manager Ingest Queue Check: HTTP {r_fs.status_code} ({len(r_fs.json())} items)")
    except Exception as e:
        print(f"[!] Warning: File Manager check: {e}")

    print("\n" + "="*70)
    print(">>> LOCAL DEPLOYMENT VERIFIED: ALL SUBSYSTEMS FULLY OPERATIONAL <<<")
    print("  - Transparent Popup UI : http://localhost:8080/")
    print("  - Orchestrator API     : http://localhost:8080/api/system/status")
    print("  - Worker Plane         : http://localhost:50051/health")
    print("  - Daemon Admin         : http://localhost:8081/health")
    if with_hotkey:
        print("  - Hotkey Active        : Press [Ctrl + Windows Key] to summon UI")
    print("="*70 + "\n")
    return procs


if __name__ == "__main__":
    with_hotkey = "--with-hotkey" in sys.argv
    procs = start_stack(with_hotkey=with_hotkey)

    if "--verify-only" in sys.argv:
        print("[*] Verification mode complete. Stopping services...")
        for p in procs:
            p.terminate()
            p.wait()
    else:
        try:
            print("[*] Running ANDA. Press Ctrl+C in this terminal to terminate all services.\n")
            while True:
                time.sleep(1.0)
        except KeyboardInterrupt:
            print("\n[*] Received shutdown signal. Stopping all background processes...")
            for p in procs:
                try:
                    p.terminate()
                    p.wait(timeout=2.0)
                except Exception:
                    pass
            print("[*] All services stopped cleanly.")
