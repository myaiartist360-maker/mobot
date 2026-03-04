"""Pure-stdlib HTTP server for MOBOT web configuration UI.

Exposes:
  GET  /                          → serves index.html
  GET  /api/config                → returns config.json as JSON
  POST /api/config                → saves new config to disk
  GET  /api/status                → version + config path + bridge status
  GET  /api/channels/whatsapp/stream  → SSE: streams WhatsApp QR/login output
  POST /api/channels/whatsapp/stop    → kill the login process
  POST /api/shutdown              → graceful server shutdown
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from mobot import __version__

# Shared state for the WhatsApp login process
_wa_proc: subprocess.Popen | None = None
_wa_lock = threading.Lock()


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
    here = Path(__file__).parent
    return (here / "index.html").read_text(encoding="utf-8")


def _get_bridge_dir() -> Path | None:
    """Find the WhatsApp bridge directory — mirrors CLI logic exactly."""
    # Primary: user's built bridge
    user_bridge = Path.home() / ".mobot" / "bridge"
    if (user_bridge / "dist" / "index.js").exists():
        return user_bridge

    # Fallback: package-installed bridge (unbuilt — npm start should still work)
    pkg_bridge = Path(__file__).parent.parent / "bridge"
    if (pkg_bridge / "package.json").exists():
        return pkg_bridge

    # Dev/repo root fallback
    src_bridge = Path(__file__).parent.parent.parent / "bridge"
    if (src_bridge / "package.json").exists():
        return src_bridge

    return None


def _stream_whatsapp_login(wfile, flush_fn):
    """Spawn the WhatsApp bridge login process and stream output as SSE."""
    global _wa_proc

    def sse(event: str, data: str):
        payload = f"event: {event}\ndata: {json.dumps(data)}\n\n"
        try:
            wfile.write(payload.encode())
            flush_fn()
        except Exception:
            pass

    bridge_dir = _get_bridge_dir()
    if not bridge_dir:
        sse("error", (
            "WhatsApp bridge source not found.\n"
            "This usually means the package is not fully installed.\n\n"
            "Try reinstalling:\n"
            "  pip install -e . --force-reinstall\n\n"
            "Or use the CLI to set up and scan QR in terminal:\n"
            "  mobot channels login\n\n"
            "(Requires Node.js ≥ 18 — https://nodejs.org)"
        ))
        sse("done", "failed")
        return

    # If bridge exists but not yet built (no dist/index.js), build it first
    if not (bridge_dir / "dist" / "index.js").exists():
        sse("status", f"Building bridge at {bridge_dir} (this runs npm install + npm run build)...")
        import shutil
        if not shutil.which("npm"):
            sse("error", "npm not found. Please install Node.js ≥ 18 (https://nodejs.org)")
            sse("done", "failed")
            return
        try:
            subprocess.run(["npm", "install"], cwd=str(bridge_dir), check=True, capture_output=True)
            subprocess.run(["npm", "run", "build"], cwd=str(bridge_dir), check=True, capture_output=True)
            sse("status", "Bridge built successfully. Starting login...")
        except subprocess.CalledProcessError as e:
            sse("error", f"Build failed: {e}")
            sse("done", "failed")
            return

    config = _load_raw()
    env = {**os.environ}
    token = config.get("channels", {}).get("whatsapp", {}).get("bridgeToken", "")
    if token:
        env["BRIDGE_TOKEN"] = token

    sse("status", f"Starting WhatsApp bridge from {bridge_dir}...")

    try:
        with _wa_lock:
            _wa_proc = subprocess.Popen(
                ["npm", "start"],
                cwd=str(bridge_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                text=True,
                bufsize=1,
            )
            proc = _wa_proc

        sse("status", "Bridge started — waiting for QR code...")

        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue
            # Detect QR code data lines (contain long base64-like strings used for QR)
            if "=" in line and len(line) > 40 and "," in line:
                sse("qr", line)  # raw QR data for JS QR renderer
            else:
                sse("log", line)  # general log output

            if "authenticated" in line.lower() or "connected" in line.lower():
                sse("connected", "WhatsApp connected successfully!")

        proc.wait()
        sse("done", "Process ended")

    except FileNotFoundError:
        sse("error", "npm not found — please install Node.js (https://nodejs.org)")
        sse("done", "failed")
    except Exception as e:
        sse("error", str(e))
        sse("done", "failed")
    finally:
        with _wa_lock:
            _wa_proc = None


# ── HTTP Handler ──────────────────────────────────────────────────────────────

class _Handler(BaseHTTPRequestHandler):
    server: "_MOBOTServer"

    def log_message(self, fmt, *args):
        pass  # silence access log

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
            bridge_dir = _get_bridge_dir()
            with _wa_lock:
                wa_running = _wa_proc is not None and _wa_proc.poll() is None
            self._json(200, {
                "version": __version__,
                "config_path": str(_config_path()),
                "config_exists": _config_path().exists(),
                "whatsapp_bridge_dir": str(bridge_dir) if bridge_dir else None,
                "whatsapp_login_active": wa_running,
            })

        elif path == "/api/channels/whatsapp/stream":
            # Server-Sent Events stream — runs the login process and streams output
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()

            try:
                _stream_whatsapp_login(self.wfile, lambda: self.wfile.flush())
            except Exception:
                pass

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

        elif path == "/api/channels/whatsapp/stop":
            global _wa_proc
            with _wa_lock:
                if _wa_proc and _wa_proc.poll() is None:
                    _wa_proc.terminate()
                    _wa_proc = None
                    self._json(200, {"ok": True, "message": "Login process stopped"})
                else:
                    self._json(200, {"ok": True, "message": "No active login process"})

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
        # Clean up any running login process
        with _wa_lock:
            if _wa_proc and _wa_proc.poll() is None:
                _wa_proc.terminate()
