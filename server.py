"""
Omni-Operator Web Server
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
        print(f"[*] Omni-Operator UI running at: http://localhost:{PORT}")
        print(f"[*] Serving files from: {FRONTEND_DIR}")

    try:
        httpd.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run()
