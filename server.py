"""
Omni-Operator Web Server
Serves the transparent popup UI frontend on the configured ORCHESTRATOR_PORT (8080).
Uses Python standard library http.server for zero overhead and high stability.
"""

import os
import sys
import functools
from http.server import HTTPServer, SimpleHTTPRequestHandler

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


def run():
    server_address = ("0.0.0.0", PORT)
    httpd = HTTPServer(server_address, OmniHandler)
    print(f"[*] Omni-Operator UI running at: http://localhost:{PORT}")
    print(f"[*] Serving files from: {FRONTEND_DIR}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server stopped.")


if __name__ == "__main__":
    run()
