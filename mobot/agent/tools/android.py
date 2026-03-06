"""Android device control tool using ADB or Termux shell commands."""

import asyncio
import os
import shutil
from pathlib import Path
from typing import Any

from mobot.agent.tools.base import Tool


class AndroidControlTool(Tool):
    """
    Tool to control an Android device via ADB (from PC) or Termux shell (on-device).

    In 'adb' mode commands are prefixed with 'adb shell' (or 'adb -s <serial> shell').
    In 'termux' mode commands are run directly in the local shell (assumes running inside Termux).
    In 'auto' mode the tool detects which is available at first use.
    """

    _MODE_UNDETECTED = "auto"

    ACTIONS = {
        "list_apps": "List installed user apps (package names)",
        "launch_app": "Launch an app by package name (e.g. com.google.android.gm)",
        "tap": "Tap a screen coordinate: requires x and y parameters",
        "swipe": "Swipe on screen: requires x1, y1, x2, y2 and optional duration_ms (default 300)",
        "screenshot": "Take a screenshot and save it to the device; returns the saved path",
        "get_screen_text": "Dump current UI screen text via uiautomator",
        "send_key": "Send a keyevent (e.g. KEYCODE_HOME, KEYCODE_BACK, KEYCODE_POWER)",
        "send_email_intent": "Open email compose via Android Intent (to, subject, body params)",
        "type_text": "Type text on the currently focused input field",
        "press_back": "Press the Back button",
        "press_home": "Press the Home button",
        "open_settings": "Open Android Settings app",
        "share_file": "Share a file via Android share sheet (requires file_path param)",
    }

    def __init__(self, mode: str = "auto", adb_serial: str = "", screenshots_dir: str = "/sdcard/DCIM/MOBOT"):
        self._mode = mode  # "auto", "adb", or "termux"
        self._adb_serial = adb_serial
        self._screenshots_dir = screenshots_dir
        self._detected_mode: str | None = None  # cached after first auto-detect

    @property
    def name(self) -> str:
        return "android_control"

    @property
    def description(self) -> str:
        return (
            "Control an Android device: launch apps, navigate UI, take screenshots, send email, "
            "share files. Works via ADB (from PC) or directly in Termux (on-device). "
            f"Available actions: {', '.join(self.ACTIONS.keys())}."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": f"Action to perform. One of: {', '.join(self.ACTIONS.keys())}",
                    "enum": list(self.ACTIONS.keys()),
                },
                "package": {
                    "type": "string",
                    "description": "App package name (e.g. com.google.android.gm). Used by launch_app.",
                },
                "x": {"type": "integer", "description": "X coordinate for tap"},
                "y": {"type": "integer", "description": "Y coordinate for tap"},
                "x1": {"type": "integer", "description": "Start X for swipe"},
                "y1": {"type": "integer", "description": "Start Y for swipe"},
                "x2": {"type": "integer", "description": "End X for swipe"},
                "y2": {"type": "integer", "description": "End Y for swipe"},
                "duration_ms": {"type": "integer", "description": "Duration in ms for swipe (default 300)"},
                "keycode": {
                    "type": "string",
                    "description": "Android keycode (e.g. KEYCODE_HOME, KEYCODE_BACK, KEYCODE_POWER, KEYCODE_VOLUME_UP)",
                },
                "text": {"type": "string", "description": "Text to type on screen"},
                "to": {"type": "string", "description": "Recipient email address for send_email_intent"},
                "subject": {"type": "string", "description": "Email subject for send_email_intent"},
                "body": {"type": "string", "description": "Email body for send_email_intent"},
                "file_path": {"type": "string", "description": "Full path to file on device for share_file"},
                "filename": {
                    "type": "string",
                    "description": "Custom filename for screenshot (without extension, default: mobot_screenshot)",
                },
            },
            "required": ["action"],
        }

    # -------------------------------------------------------------------------
    # Mode detection
    # -------------------------------------------------------------------------

    def _resolve_mode(self) -> str:
        """Return 'adb' or 'termux' — detect once then cache."""
        if self._mode != self._MODE_UNDETECTED:
            return self._mode
        if self._detected_mode:
            return self._detected_mode

        # Running inside Termux if PREFIX env var is set
        if os.environ.get("PREFIX", "").startswith("/data/data/com.termux"):
            self._detected_mode = "termux"
            return "termux"

        # Check if adb is on PATH
        if shutil.which("adb"):
            self._detected_mode = "adb"
            return "adb"

        # Default to termux (assume running on device)
        self._detected_mode = "termux"
        return "termux"

    def _shell_prefix(self) -> list[str]:
        """Return command prefix list for the current mode."""
        mode = self._resolve_mode()
        if mode == "adb":
            cmd = ["adb"]
            if self._adb_serial:
                cmd += ["-s", self._adb_serial]
            cmd += ["shell"]
            return cmd
        return []  # Termux: run directly

    async def _run(self, *args: str) -> tuple[int, str]:
        """Execute a shell command with optional adb prefix. Returns (returncode, output)."""
        prefix = self._shell_prefix()
        full_cmd = prefix + list(args)
        try:
            proc = await asyncio.create_subprocess_exec(
                *full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
            return proc.returncode or 0, stdout.decode("utf-8", errors="replace").strip()
        except asyncio.TimeoutError:
            return 1, "Error: Command timed out after 30 seconds"
        except FileNotFoundError as e:
            return 1, f"Error: Command not found — {e}"
        except Exception as e:
            return 1, f"Error: {e}"

    # -------------------------------------------------------------------------
    # Action handlers
    # -------------------------------------------------------------------------

    async def _list_apps(self) -> str:
        rc, out = await self._run("pm", "list", "packages", "-3")
        if rc != 0:
            return f"Error listing apps: {out}"
        packages = [line.replace("package:", "").strip() for line in out.splitlines() if line.startswith("package:")]
        return "Installed user apps:\n" + "\n".join(packages) if packages else "No user-installed apps found."

    async def _launch_app(self, package: str) -> str:
        if not package:
            return "Error: 'package' parameter is required for launch_app"
        # Use monkey to launch the app's main activity
        rc, out = await self._run("monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1")
        if rc != 0 or "error" in out.lower():
            # Fallback: try am start with explicit launcher activity
            rc2, out2 = await self._run("am", "start", "-n", f"{package}/.MainActivity")
            if rc2 != 0:
                return f"Could not launch {package}.\nmonkey output: {out}\nam output: {out2}"
            return f"Launched {package} (via am start)."
        return f"Launched {package}."

    async def _tap(self, x: int, y: int) -> str:
        rc, out = await self._run("input", "tap", str(x), str(y))
        return f"Tapped ({x}, {y})." if rc == 0 else f"Tap failed: {out}"

    async def _swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> str:
        rc, out = await self._run("input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms))
        return f"Swiped ({x1},{y1}) → ({x2},{y2}) in {duration_ms}ms." if rc == 0 else f"Swipe failed: {out}"

    async def _screenshot(self, filename: str = "mobot_screenshot") -> str:
        mode = self._resolve_mode()
        # Ensure directory exists on device
        dir_path = self._screenshots_dir
        await self._run("mkdir", "-p", dir_path)
        remote_path = f"{dir_path}/{filename}.png"

        if mode == "termux":
            # Try Termux:API first (higher quality, saves to gallery)
            rc, out = await self._run("termux-screenshot", "-f", remote_path)
            if rc != 0:
                # Fallback to screencap (requires root or shell permission on most devices)
                rc, out = await self._run("screencap", "-p", remote_path)
        else:
            # ADB mode: screencap via adb shell
            rc, out = await self._run("screencap", "-p", remote_path)

        if rc != 0:
            return f"Screenshot failed: {out}\nTip: On non-rooted devices, grant WRITE_EXTERNAL_STORAGE permission or use Termux:API."
        return f"Screenshot saved to {remote_path} on the device.\nTo retrieve via ADB: adb pull {remote_path}"

    async def _get_screen_text(self) -> str:
        rc, out = await self._run("uiautomator", "dump", "/dev/stdout")
        if rc != 0 or not out:
            return f"Could not dump UI: {out}"
        # Extract text attributes from XML
        import re
        texts = re.findall(r'text="([^"]+)"', out)
        content_descs = re.findall(r'content-desc="([^"]+)"', out)
        all_text = list(dict.fromkeys(t for t in texts + content_descs if t))  # deduplicate
        if not all_text:
            return "No visible text found on screen."
        return "Visible screen text:\n" + "\n".join(f"  • {t}" for t in all_text[:60])

    async def _send_key(self, keycode: str) -> str:
        if not keycode:
            return "Error: 'keycode' parameter required"
        # Normalize: prefix KEYCODE_ if not present
        if not keycode.upper().startswith("KEYCODE_"):
            keycode = f"KEYCODE_{keycode.upper()}"
        rc, out = await self._run("input", "keyevent", keycode)
        return f"Sent keyevent {keycode}." if rc == 0 else f"Keyevent failed: {out}"

    async def _send_email_intent(self, to: str = "", subject: str = "", body: str = "") -> str:
        if not to:
            return "Error: 'to' (recipient email) is required for send_email_intent"
        import urllib.parse
        uri = f"mailto:{urllib.parse.quote(to)}"
        extras = []
        if subject:
            extras += ["--es", "android.intent.extra.SUBJECT", subject]
        if body:
            extras += ["--es", "android.intent.extra.TEXT", body]
        cmd = ["am", "start", "-a", "android.intent.action.SENDTO", "-d", uri] + extras
        rc, out = await self._run(*cmd)
        if rc != 0:
            return f"Failed to open email compose: {out}"
        return (
            f"Email compose opened for {to}. "
            "Now use get_screen_text or screenshot to locate the Send button, "
            "then use tap to click Send — do NOT ask the user to do this."
        )

    async def _type_text(self, text: str) -> str:
        if not text:
            return "Error: 'text' parameter required"
        # Escape special chars for adb shell input
        escaped = text.replace(" ", "%s").replace("'", "\\'")
        rc, out = await self._run("input", "text", escaped)
        return f"Typed text: {text}" if rc == 0 else f"Type failed: {out}"

    async def _press_back(self) -> str:
        return await self._send_key("KEYCODE_BACK")

    async def _press_home(self) -> str:
        return await self._send_key("KEYCODE_HOME")

    async def _open_settings(self) -> str:
        rc, out = await self._run("am", "start", "-a", "android.settings.SETTINGS")
        return "Opened Android Settings." if rc == 0 else f"Failed to open settings: {out}"

    async def _share_file(self, file_path: str) -> str:
        if not file_path:
            return "Error: 'file_path' parameter required"
        mode = self._resolve_mode()
        if mode == "termux":
            rc, out = await self._run("termux-share", file_path)
            return f"Share sheet opened for {file_path}." if rc == 0 else f"Share failed: {out}\nTip: Install Termux:API for sharing support."
        else:
            # ADB: use am start with ACTION_SEND intent
            rc, out = await self._run(
                "am", "start", "-a", "android.intent.action.SEND",
                "--eu", "android.intent.extra.STREAM", f"file://{file_path}",
                "-t", "*/*",
            )
            return f"Share sheet opened for {file_path}." if rc == 0 else f"Share failed: {out}"

    # -------------------------------------------------------------------------
    # Dispatch
    # -------------------------------------------------------------------------

    async def execute(self, action: str, **kwargs: Any) -> str:
        mode = self._resolve_mode()
        header = f"[Android:{mode}] "

        dispatch = {
            "list_apps": lambda: self._list_apps(),
            "launch_app": lambda: self._launch_app(kwargs.get("package", "")),
            "tap": lambda: self._tap(kwargs.get("x", 0), kwargs.get("y", 0)),
            "swipe": lambda: self._swipe(
                kwargs.get("x1", 0), kwargs.get("y1", 0),
                kwargs.get("x2", 0), kwargs.get("y2", 0),
                kwargs.get("duration_ms", 300),
            ),
            "screenshot": lambda: self._screenshot(kwargs.get("filename", "mobot_screenshot")),
            "get_screen_text": lambda: self._get_screen_text(),
            "send_key": lambda: self._send_key(kwargs.get("keycode", "")),
            "send_email_intent": lambda: self._send_email_intent(
                kwargs.get("to", ""), kwargs.get("subject", ""), kwargs.get("body", "")
            ),
            "type_text": lambda: self._type_text(kwargs.get("text", "")),
            "press_back": lambda: self._press_back(),
            "press_home": lambda: self._press_home(),
            "open_settings": lambda: self._open_settings(),
            "share_file": lambda: self._share_file(kwargs.get("file_path", "")),
        }

        handler = dispatch.get(action)
        if not handler:
            return f"Unknown action: '{action}'. Available: {', '.join(self.ACTIONS.keys())}"
        result = await handler()
        return header + result
