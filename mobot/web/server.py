"""Pure-stdlib HTTP server for MOBOT web configuration UI.

Exposes:
  GET  /            → serves index.html (the config UI)
  GET  /api/config  → returns current config.json as JSON
  POST /api/config  → merges posted JSON into config.json
  GET  /api/status  → mobot version + config path
  POST /api/shutdown → graceful shutdown
"""

from __future__ import annotations

import json
import os
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from mobot import __version__


def _config_path() -> Path:
    from mobot.config.loader import get_config_path
    return get_config_path()


def _load_raw() -> dict:
    p = _config_path()
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def _save_raw(data: dict) -> None:
    p = _config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _index_html() -> str:
    """Return the path of index.html bundled next to this file."""
    here = Path(__file__).parent
    return (here / "index.html").read_text(encoding="utf-8")


# ── HTTP Handler ─────────────────────────────────────────────────────────────

class _Handler(BaseHTTPRequestHandler):
    server: "_MOBOTServer"

    def log_message(self, fmt, *args):  # silence default access log
        pass

    def _send(self, code: int, content_type: str, body: str | bytes) -> None:
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, data: dict) -> None:
        self._send(code, "application/json", json.dumps(data, ensure_ascii=False))

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            try:
                html = _index_html()
                self._send(200, "text/html; charset=utf-8", html)
            except Exception as e:
                self._send(500, "text/plain", f"Error loading UI: {e}")
        elif path == "/api/config":
            self._json(200, _load_raw())
        elif path == "/api/status":
            self._json(200, {
                "version": __version__,
                "config_path": str(_config_path()),
                "config_exists": _config_path().exists(),
            })
        else:
            self._send(404, "text/plain", "Not found")

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/api/config":
            try:
                new_data = self._read_body()
                _save_raw(new_data)
                self._json(200, {"ok": True, "message": "Config saved successfully"})
            except Exception as e:
                self._json(500, {"ok": False, "message": str(e)})
        elif path == "/api/shutdown":
            self._json(200, {"ok": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
        else:
            self._send(404, "text/plain", "Not found")


class _MOBOTServer(HTTPServer):
    pass


# ── Public API ────────────────────────────────────────────────────────────────

def run(port: int = 7891, open_browser: bool = True, host: str = "127.0.0.1") -> None:
    """Start the MOBOT web config server."""
    server = _MOBOTServer((host, port), _Handler)

    url = f"http://{host}:{port}"
    print(f"\n🤖 MOBOT Web Config UI")
    print(f"   URL: {url}")
    print(f"   Config: {_config_path()}")
    print(f"\n   Press Ctrl+C to stop.\n")

    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n✓ Web server stopped.")
