"""Pure-stdlib HTTP server for MOBOT web configuration UI.

Endpoints:
  GET  /                              → index.html
  GET  /api/config                    → config.json as JSON
  POST /api/config                    → save config.json
  GET  /api/status                    → version, config path, agent/bridge status
  GET  /api/ollama/models?base=URL    → list installed Ollama models
  GET  /api/ollama/test?base=URL      → test Ollama connectivity + latency
  GET  /api/channels/whatsapp/stream  → SSE: WhatsApp QR login stream
  POST /api/channels/whatsapp/stop    → kill WhatsApp login process
  POST /api/agent/start               → start mobot agent (one-shot)
  GET  /api/agent/stream              → SSE: live agent stdout
  POST /api/agent/stop                → kill running agent
  GET  /api/logs?lines=N              → last N log lines (ring buffer + log file)
  GET  /api/tools                     → tool catalog + current enabled state
  POST /api/tools/save                → save disabled tools list to config
  POST /api/shutdown                  → graceful server shutdown
"""

from __future__ import annotations

import collections
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from mobot import __version__

# ── Shared state ──────────────────────────────────────────────────────────────

# WhatsApp login process
_wa_proc: subprocess.Popen | None = None
_wa_lock = threading.Lock()

# Live agent process
_agent_proc: subprocess.Popen | None = None
_agent_lock = threading.Lock()

# Always-on gateway process (mobot gateway)
_gw_proc: subprocess.Popen | None = None
_gw_lock = threading.Lock()

# In-memory log ring buffer (last 500 lines)
_log_buffer: collections.deque[str] = collections.deque(maxlen=500)
_log_lock = threading.Lock()


def _kill_process_on_port(port: int) -> None:
    """Best-effort: kill any process listening on the given TCP port."""
    try:
        import signal as _signal
        # Linux / Android / macOS: use fuser
        result = subprocess.run(
            ["fuser", "-k", f"{port}/tcp"],
            capture_output=True, timeout=5,
        )
        if result.returncode == 0:
            time.sleep(0.5)  # give the OS a moment to release the port
    except FileNotFoundError:
        pass  # fuser not available — try lsof
    except Exception:
        pass
    try:
        # Fallback: lsof (macOS / some Linuxes)
        r = subprocess.run(
            ["lsof", "-ti", f"tcp:{port}"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            for pid_str in r.stdout.strip().split():
                try:
                    os.kill(int(pid_str), 15)  # SIGTERM
                except Exception:
                    pass
            time.sleep(0.5)
    except FileNotFoundError:
        pass
    except Exception:
        pass



def _log(line: str) -> None:
    with _log_lock:
        _log_buffer.append(f"[{_ts()}] {line}")


def _ts() -> str:
    import datetime
    return datetime.datetime.now().strftime("%H:%M:%S")


# ── Helpers ───────────────────────────────────────────────────────────────────

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
    user_bridge = Path.home() / ".mobot" / "bridge"
    if (user_bridge / "dist" / "index.js").exists():
        return user_bridge
    pkg_bridge = Path(__file__).parent.parent / "bridge"
    if (pkg_bridge / "package.json").exists():
        return pkg_bridge
    src_bridge = Path(__file__).parent.parent.parent / "bridge"
    if (src_bridge / "package.json").exists():
        return src_bridge
    return None


def _mobot_bin() -> str:
    """Find the mobot executable."""
    # Try the same Python environment's mobot
    here = Path(sys.executable).parent
    for name in ("mobot", "mobot.exe"):
        p = here / name
        if p.exists():
            return str(p)
    # Try PATH
    found = shutil.which("mobot")
    if found:
        return found
    # Last resort: run as module
    return f"{sys.executable} -m mobot"


# ── Tool catalog ──────────────────────────────────────────────────────────────

TOOL_CATALOG = [
    {
        "name": "android_control",
        "category": "Android",
        "emoji": "📱",
        "description": "Control Android device: tap, swipe, screenshot, launch apps, type text, send email.",
        "actions": [
            {"name": "list_apps",       "desc": "List all installed user apps"},
            {"name": "launch_app",      "desc": "Open an app by package name"},
            {"name": "tap",             "desc": "Tap screen at (x, y)"},
            {"name": "swipe",           "desc": "Swipe between two points"},
            {"name": "screenshot",      "desc": "Capture screen to /sdcard/DCIM/MOBOT/"},
            {"name": "get_screen_text", "desc": "Read current UI text via uiautomator"},
            {"name": "send_key",        "desc": "Send keyevent (HOME, BACK, POWER, etc.)"},
            {"name": "send_email_intent","desc": "Open email compose via Android Intent"},
            {"name": "type_text",       "desc": "Type text into focused field"},
            {"name": "press_back",      "desc": "Press Back button"},
            {"name": "press_home",      "desc": "Go to Home screen"},
            {"name": "open_settings",   "desc": "Open Android Settings"},
            {"name": "share_file",      "desc": "Share a file via Android share sheet"},
        ],
    },
    {
        "name": "exec",
        "category": "Shell",
        "emoji": "💻",
        "description": "Execute shell commands. Safety guard blocks dangerous patterns (rm -rf, format, etc.).",
        "actions": [],
    },
    {
        "name": "read_file",
        "category": "Files",
        "emoji": "📖",
        "description": "Read the contents of a file.",
        "actions": [],
    },
    {
        "name": "write_file",
        "category": "Files",
        "emoji": "✏️",
        "description": "Write content to a file (creates parent dirs if needed).",
        "actions": [],
    },
    {
        "name": "edit_file",
        "category": "Files",
        "emoji": "🔄",
        "description": "Edit a file by find-and-replace. Old text must exist exactly.",
        "actions": [],
    },
    {
        "name": "list_dir",
        "category": "Files",
        "emoji": "📂",
        "description": "List directory contents.",
        "actions": [],
    },
    {
        "name": "web_search",
        "category": "Web",
        "emoji": "🔍",
        "description": "Search the web via Brave Search API. Requires Brave API key in config.",
        "actions": [],
    },
    {
        "name": "web_fetch",
        "category": "Web",
        "emoji": "🌐",
        "description": "Fetch a URL and extract readable text content (HTML → markdown).",
        "actions": [],
    },
    {
        "name": "cron",
        "category": "Schedule",
        "emoji": "⏰",
        "description": "Add, list, and remove timed/scheduled tasks.",
        "actions": [],
    },
    {
        "name": "mcp",
        "category": "MCP",
        "emoji": "🔌",
        "description": "Model Context Protocol — runs external tool servers defined in config.",
        "actions": [],
    },
    {
        "name": "spawn",
        "category": "Process",
        "emoji": "🚀",
        "description": "Spawn long-running background processes.",
        "actions": [],
    },
]


# ── SSE helpers ───────────────────────────────────────────────────────────────

def _write_sse(wfile, flush_fn, event: str, data: str) -> bool:
    """Write one SSE frame. Returns False if write failed (client disconnected)."""
    payload = f"event: {event}\ndata: {json.dumps(data)}\n\n"
    try:
        wfile.write(payload.encode())
        flush_fn()
        return True
    except Exception:
        return False


# ── WhatsApp login stream ─────────────────────────────────────────────────────

def _stream_whatsapp_login(wfile, flush_fn):
    global _wa_proc

    def sse(event, data): return _write_sse(wfile, flush_fn, event, data)

    bridge_dir = _get_bridge_dir()
    if not bridge_dir:
        sse("error", "WhatsApp bridge source not found.\nTry: pip install -e . --force-reinstall\nOr use terminal: mobot channels login\n(Requires Node.js ≥18)")
        sse("done", "failed")
        return

    if not (bridge_dir / "dist" / "index.js").exists():
        sse("status", f"Building bridge at {bridge_dir}…")
        if not shutil.which("npm"):
            sse("error", "npm not found — install Node.js ≥18 (https://nodejs.org)")
            sse("done", "failed")
            return
        try:
            subprocess.run(["npm", "install"], cwd=str(bridge_dir), check=True, capture_output=True)
            subprocess.run(["npm", "run", "build"], cwd=str(bridge_dir), check=True, capture_output=True)
            sse("status", "Bridge built. Starting login…")
        except subprocess.CalledProcessError as e:
            sse("error", f"Build failed: {e}")
            sse("done", "failed")
            return

    config = _load_raw()
    env = {**os.environ}
    token = config.get("channels", {}).get("whatsapp", {}).get("bridgeToken", "")
    if token:
        env["BRIDGE_TOKEN"] = token

    # ── Kill any stale process already on port 3001 (EADDRINUSE prevention) ──
    with _wa_lock:
        if _wa_proc and _wa_proc.poll() is None:
            _log("[wa] Terminating existing bridge before restart")
            _wa_proc.terminate()
            try:
                _wa_proc.wait(timeout=3)
            except Exception:
                _wa_proc.kill()

    sse("status", "Clearing port 3001…")
    _kill_process_on_port(3001)

    sse("status", "Starting bridge…")
    connected = False
    try:
        with _wa_lock:
            _wa_proc = subprocess.Popen(
                ["npm", "start"], cwd=str(bridge_dir),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                env=env, text=True, bufsize=1,
            )
            proc = _wa_proc

        sse("status", "Bridge started — waiting for QR…")
        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue
            if "=" in line and len(line) > 40 and "," in line:
                sse("qr", line)
            else:
                sse("log", line)
            if "authenticated" in line.lower() or "connected" in line.lower():
                if not connected:
                    connected = True
                    sse("connected", "WhatsApp connected!")
                    _log("[wa] WhatsApp connected")
        proc.wait()
        msg = "Session saved — bridge is running in background" if connected else "Process ended"
        sse("done", msg)
    except FileNotFoundError:
        sse("error", "npm not found — install Node.js")
        sse("done", "failed")
    except Exception as e:
        sse("error", str(e))
        sse("done", "failed")
    # NOTE: _wa_proc intentionally NOT cleared in finally — bridge keeps running


# ── Live agent stream ─────────────────────────────────────────────────────────

def _stream_agent(wfile, flush_fn, message: str):
    global _agent_proc

    def sse(event, data): return _write_sse(wfile, flush_fn, event, data)

    mobot = _mobot_bin()
    _log(f"[agent] Starting: {message[:80]}")
    sse("status", "Starting agent…")

    try:
        cmd = mobot.split() + ["agent", "--no-markdown", "-m", message]
        with _agent_lock:
            _agent_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
            proc = _agent_proc

        for line in proc.stdout:
            line = line.rstrip()
            _log(f"[agent] {line}")
            if not sse("chunk", line):
                break  # client disconnected

        proc.wait()
        sse("done", f"Exit code: {proc.returncode}")
        _log(f"[agent] Done (exit {proc.returncode})")
    except FileNotFoundError:
        msg = "mobot binary not found. Make sure MOBOT is installed (pip install -e .)"
        sse("error", msg)
        _log(f"[agent] ERROR: {msg}")
        sse("done", "failed")
    except Exception as e:
        sse("error", str(e))
        _log(f"[agent] ERROR: {e}")
        sse("done", "failed")
    finally:
        with _agent_lock:
            _agent_proc = None


# ── HTTP Handler ──────────────────────────────────────────────────────────────

class _Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args): pass  # silence access log

    def _send(self, code: int, ctype: str, body: str | bytes) -> None:
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, data) -> None:
        self._send(code, "application/json", json.dumps(data, ensure_ascii=False))

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw)

    def _qs(self) -> dict:
        import urllib.parse
        qs_str = self.path.split("?", 1)[1] if "?" in self.path else ""
        return {k: v[0] for k, v in urllib.parse.parse_qs(qs_str).items()}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _start_sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        qs = self._qs()

        if path == "/":
            try:
                self._send(200, "text/html; charset=utf-8", _index_html())
            except Exception as e:
                self._send(500, "text/plain", f"Error loading UI: {e}")

        elif path == "/api/config":
            self._json(200, _load_raw())

        elif path == "/api/status":
            bridge_dir = _get_bridge_dir()
            with _wa_lock:
                wa_running = _wa_proc is not None and _wa_proc.poll() is None
            with _agent_lock:
                agent_running = _agent_proc is not None and _agent_proc.poll() is None
            with _gw_lock:
                gw_running = _gw_proc is not None and _gw_proc.poll() is None
            self._json(200, {
                "version": __version__,
                "config_path": str(_config_path()),
                "config_exists": _config_path().exists(),
                "whatsapp_bridge_dir": str(bridge_dir) if bridge_dir else None,
                "whatsapp_login_active": wa_running,
                "agent_running": agent_running,
                "gateway_running": gw_running,
            })

        elif path == "/api/ollama/models":
            import urllib.request
            base = qs.get("base", "http://localhost:11434").rstrip("/")
            try:
                req = urllib.request.urlopen(f"{base}/api/tags", timeout=5)
                data = json.loads(req.read())
                models = [m["name"] for m in data.get("models", [])]
                self._json(200, {"ok": True, "models": models, "base": base})
            except Exception as e:
                self._json(200, {"ok": False, "models": [], "error": str(e),
                                 "hint": "Make sure Ollama is running: ollama serve"})

        elif path == "/api/ollama/test":
            import urllib.request
            base = qs.get("base", "http://localhost:11434").rstrip("/")
            t0 = time.time()
            try:
                req = urllib.request.urlopen(f"{base}/api/tags", timeout=5)
                data = json.loads(req.read())
                latency_ms = int((time.time() - t0) * 1000)
                models = data.get("models", [])
                self._json(200, {
                    "ok": True,
                    "latency_ms": latency_ms,
                    "model_count": len(models),
                    "base": base,
                    "message": f"Connected — {len(models)} model(s) installed, {latency_ms}ms",
                })
            except Exception as e:
                self._json(200, {
                    "ok": False,
                    "error": str(e),
                    "hint": "Run: ollama serve",
                    "message": f"Connection failed: {e}",
                })

        elif path == "/api/tools":
            config = _load_raw()
            disabled = set(config.get("agents", {}).get("defaults", {}).get("disabledTools", []))
            catalog = []
            for tool in TOOL_CATALOG:
                catalog.append({**tool, "enabled": tool["name"] not in disabled})
            self._json(200, {"tools": catalog, "disabled": list(disabled)})

        elif path == "/api/logs":
            n = int(qs.get("lines", "200"))
            lines = []
            # Try reading from log file
            log_file = Path.home() / ".mobot" / "mobot.log"
            if log_file.exists():
                try:
                    all_lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
                    lines = all_lines[-n:]
                except Exception:
                    pass
            # Append in-memory buffer
            with _log_lock:
                lines += list(_log_buffer)
            lines = lines[-n:]
            self._json(200, {"lines": lines, "count": len(lines)})

        elif path == "/api/agent/stream":
            message = qs.get("message", "Hello!")
            self._start_sse()
            try:
                _stream_agent(self.wfile, lambda: self.wfile.flush(), message)
            except Exception:
                pass

        elif path == "/api/channels/whatsapp/stream":
            self._start_sse()
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
                _log("[config] Config saved")
                self._json(200, {"ok": True, "message": "Config saved successfully"})
            except Exception as e:
                self._json(500, {"ok": False, "message": str(e)})

        elif path == "/api/tools/save":
            try:
                body = self._read_body()
                disabled = body.get("disabledTools", [])
                data = _load_raw()
                data.setdefault("agents", {}).setdefault("defaults", {})["disabledTools"] = disabled
                _save_raw(data)
                _log(f"[tools] Saved permissions — disabled: {disabled}")
                self._json(200, {"ok": True, "disabled": disabled})
            except Exception as e:
                self._json(500, {"ok": False, "message": str(e)})

        elif path == "/api/agent/stop":
            global _agent_proc
            with _agent_lock:
                if _agent_proc and _agent_proc.poll() is None:
                    _agent_proc.terminate()
                    _agent_proc = None
                    self._json(200, {"ok": True, "message": "Agent stopped"})
                else:
                    self._json(200, {"ok": True, "message": "No active agent"})

        elif path == "/api/gateway/start":
            global _gw_proc
            with _gw_lock:
                if _gw_proc and _gw_proc.poll() is None:
                    self._json(200, {"ok": True, "message": "Gateway already running"})
                    return
            mobot = _mobot_bin()
            cmd = mobot.split() + ["gateway"]
            try:
                with _gw_lock:
                    _gw_proc = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, bufsize=1,
                    )

                def _tail():
                    for line in _gw_proc.stdout:
                        _log(f"[gateway] {line.rstrip()}")

                threading.Thread(target=_tail, daemon=True).start()
                _log("[gateway] Started")
                self._json(200, {"ok": True, "message": "Gateway started"})
            except Exception as e:
                self._json(500, {"ok": False, "message": str(e)})

        elif path == "/api/gateway/stop":
            global _gw_proc
            with _gw_lock:
                if _gw_proc and _gw_proc.poll() is None:
                    _gw_proc.terminate()
                    _gw_proc = None
                    _log("[gateway] Stopped")
                    self._json(200, {"ok": True, "message": "Gateway stopped"})
                else:
                    self._json(200, {"ok": True, "message": "Gateway not running"})

        elif path == "/api/channels/whatsapp/stop":
            global _wa_proc
            with _wa_lock:
                if _wa_proc and _wa_proc.poll() is None:
                    _wa_proc.terminate()
                    _wa_proc = None
                    _log("[wa] Bridge stopped by user")
                    self._json(200, {"ok": True, "message": "WhatsApp bridge stopped"})
                else:
                    # Also try killing port 3001 for any external bridge
                    _kill_process_on_port(3001)
                    self._json(200, {"ok": True, "message": "No active bridge (killed port 3001)"})

        elif path == "/api/shutdown":
            self._json(200, {"ok": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()

        else:
            self._send(404, "text/plain", "Not found")


class _MOBOTServer(HTTPServer):
    allow_reuse_address = True


# ── Public API ────────────────────────────────────────────────────────────────

def run(port: int = 7891, open_browser: bool = True, host: str = "127.0.0.1") -> None:
    """Start the MOBOT web config server."""
    # Attempt to cleanly kill any running instance on this port first
    _kill_process_on_port(port)

    try:
        server = _MOBOTServer((host, port), _Handler)
    except OSError as e:
        if "Address already in use" in str(e) or getattr(e, "errno", 0) == 98:
            print(f"\n[!] Error: Port {port} is already in use.")
            print("    Another instance of 'mobot web' might be running in the background.")
            print("    Try closing it, or run this command in a new terminal to force kill it:")
            print(f"        fuser -k {port}/tcp")
            print("    (You may need to run: pkg install psmisc)\n")
            sys.exit(1)
        raise

    url = f"http://{host}:{port}"
    print(f"\n🤖 MOBOT Web Config UI")
    print(f"   URL: {url}")
    print(f"   Config: {_config_path()}")
    print(f"\n   Press Ctrl+C to stop.\n")
    _log(f"[server] Started at {url}")

    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n✓ Web server stopped.")
    finally:
        with _wa_lock:
            if _wa_proc and _wa_proc.poll() is None:
                _wa_proc.terminate()
        with _agent_lock:
            if _agent_proc and _agent_proc.poll() is None:
                _agent_proc.terminate()
