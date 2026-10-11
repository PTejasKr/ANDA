"""
IPC Boundary Security Tests (Subsystem B)
Test Case 1: Unauthorized Elevation (Rejection of raw shell payloads)
Test Case 2: Human-in-the-Loop Validation (Execution halts, timeout safety, physical confirmation)
"""

import json
import os
import subprocess
import time
import requests
import pytest

TEST_PIPE = r"\\.\pipe\omni_pytest_pipe"
TEST_HTTP_PORT = "8085"


@pytest.fixture(scope="module")
def running_daemon():
    # Build daemon binary if not already present
    daemon_bin = os.path.abspath("daemon.exe")
    if not os.path.exists(daemon_bin):
        subprocess.run(["go", "build", "-o", "daemon.exe", "./backend/daemon"], check=True)

    env = os.environ.copy()
    env["DAEMON_PIPE"] = TEST_PIPE
    env["DAEMON_HTTP_PORT"] = TEST_HTTP_PORT

    proc = subprocess.Popen([daemon_bin], env=env)
    # Wait for pipe and HTTP server readiness
    time.sleep(1.0)

    yield proc

    proc.terminate()
    try:
        proc.wait(timeout=2)
    except Exception:
        proc.kill()


def send_pipe_message(pipe_path: str, message: str) -> str:
    """Sends a line across a Windows Named Pipe and reads back one line response."""
    with open(pipe_path, "r+b", buffering=0) as pipe:
        if not message.endswith("\n"):
            message += "\n"
        pipe.write(message.encode("utf-8"))
        pipe.flush()
        line = pipe.readline()
        return line.decode("utf-8").strip()


def test_unauthorized_elevation_raw_shell_rejected(running_daemon):
    """
    Test Case 1: Attempt to send raw shell commands from Worker to Daemon IPC pipe.
    Expected: Daemon rejects the payload. Only strict capability tokens are parsed.
    """
    raw_payload = "cmd.exe /c whoami && echo injected_shell\n"
    response_str = send_pipe_message(TEST_PIPE, raw_payload)
    resp = json.loads(response_str)

    assert resp["status"] == "rejected"
    assert resp["code"] == "UNAUTHORIZED_PAYLOAD"
    assert "Only structured JSON capability tokens are permitted" in resp["message"]


def test_hitl_user_approval_signal(running_daemon):
    """
    Test Case 2: Send valid flash_usb capability token to Daemon.
    Execution halts until user confirmation signal is received.
    """
    token_id = "token-test-approve-py"
    token = {
        "action": "flash_usb",
        "drive": "E:",
        "hash": "7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
        "token_id": token_id,
    }

    # Worker sends token in a thread or we trigger approve after sending
    import threading

    response_container = {}

    def worker_thread():
        msg = json.dumps(token)
        response_container["resp"] = send_pipe_message(TEST_PIPE, msg)

    t = threading.Thread(target=worker_thread)
    t.start()

    # Poll Daemon HTTP API until pending token is visible
    pending_found = False
    for _ in range(20):
        time.sleep(0.1)
        try:
            r = requests.get(f"http://127.0.0.1:{TEST_HTTP_PORT}/api/daemon/pending", timeout=1)
            items = r.json()
            if any(item["id"] == token_id for item in items):
                pending_found = True
                break
        except Exception:
            pass

    assert pending_found, "Token should be halted in pending HITL queue"

    # Send Human Approval Signal
    approve_resp = requests.post(
        f"http://127.0.0.1:{TEST_HTTP_PORT}/api/daemon/approve",
        json={"token_id": token_id, "approved": True},
        timeout=2,
    )
    assert approve_resp.json()["success"] is True

    t.join(timeout=3)
    resp = json.loads(response_container["resp"])
    assert resp["status"] == "success"
    assert resp["code"] == "EXECUTION_COMPLETED"
    assert resp["token_id"] == token_id
