"""
ANDA Web Server
Serves the transparent popup UI frontend on the configured ORCHESTRATOR_PORT (8080).
Uses Python standard library ThreadingHTTPServer with dual-stack IPv4/IPv6 for high stability.
"""

import os
import sys
import socket
import contextlib
from http.server import ThreadingHTTPServer, HTTPServer, SimpleHTTPRequestHandler

PORT = int(os.environ.get("ORCHESTRATOR_PORT", 8080))
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")


class OmniHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def end_headers(self):
        # Allow cross-origin and disable caching during development
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path == "/install":
            self.send_response(302)
            self.send_header("Location", "/install.html")
            self.end_headers()
            return
        if self.path == "/app":
            self.send_response(302)
            self.send_header("Location", "/index.html")
            self.end_headers()
            return
        if self.path.startswith("/api/system/status"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"orchestrator":"static_fallback","worker_plane":"offline","daemon_ipc":"offline","storage_root":"storage","mode":"server_fallback"}')
            return
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"healthy"}')
            return
        super().do_GET()

    def log_message(self, format, *args):
        # Suppress noisy console logs in headless daemon mode
        if sys.stdout is not None:
            super().log_message(format, *args)


class DualStackServer(ThreadingHTTPServer):
    address_family = socket.AF_INET6

    def server_bind(self):
        with contextlib.suppress(Exception):
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        return super().server_bind()


def run():
    try:
        httpd = DualStackServer(("::", PORT), OmniHandler)
    except Exception:
        # Fallback to standard IPv4
        httpd = HTTPServer(("0.0.0.0", PORT), OmniHandler)

    if sys.stdout is not None:
        print(f"[*] ANDA UI running at: http://localhost:{PORT}")
        print(f"[*] Serving files from: {FRONTEND_DIR}")

    try:
        httpd.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run()
