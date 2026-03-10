"""Remote Web Chat channel implementation over WebSockets."""

import asyncio
import json
import base64
import time
import mimetypes
from pathlib import Path

from loguru import logger
import websockets
from websockets.server import serve
from websockets.http11 import Response, Request
from websockets.datastructures import Headers

from mobot.bus.events import OutboundMessage
from mobot.bus.queue import MessageBus
from mobot.channels.base import BaseChannel
from mobot.config.schema import WebChatConfig


class WebChatChannel(BaseChannel):
    """
    Remote Web Chat channel server.
    
    Serves both an HTML UI (via HTTP) and WebSocket connections on the same port.
    """

    name = "webchat"

    def __init__(self, config: WebChatConfig, bus: MessageBus):
        super().__init__(config, bus)
        self.config = config
        self._server = None
        # Map session_id → websocket so outbound messages can be routed to the right client
        self._sessions: dict[str, websockets.ServerConnection] = {}
        
        # Load UI HTML
        ui_path = Path(__file__).parent / "webchat_ui.html"
        if ui_path.exists():
            self._ui_html = ui_path.read_bytes()
        else:
            self._ui_html = b"<html><body>WebChat UI not found</body></html>"

    async def start(self) -> None:
        """Start the WebSocket server."""
        self._running = True
        
        logger.info(f"Starting WebChat server on ws://{self.config.host}:{self.config.port}")
        
        self._server = await serve(
            self._handle_ws_connection,
            self.config.host,
            self.config.port,
            process_request=self._process_http_request
        )

        while self._running:
            await asyncio.sleep(1)
            
    async def stop(self) -> None:
        """Stop the WebSocket server."""
        self._running = False
        if self._server:
            logger.info("Stopping WebChat server...")
            self._server.close()
            await self._server.wait_closed()
            self._server = None
            
        # Disconnect all clients
        for ws in list(self._sessions.values()):
            await ws.close()
        self._sessions.clear()

    async def _process_http_request(self, connection, request: Request):
        """Serve the HTML UI on HTTP GET /. Return None to allow WebSocket upgrade."""
        if request.path == "/":
            headers = Headers([
                ("Content-Type", "text/html; charset=utf-8"),
                ("Content-Length", str(len(self._ui_html))),
                ("Connection", "close"),
            ])
            return Response(status_code=200, headers=headers, body=self._ui_html)
        # For all other paths (including WebSocket upgrade), return None to proceed normally
        return None

    async def _handle_ws_connection(self, websocket) -> None:
        """Handle incoming WebSocket connection from the Web UI."""
        client_address = websocket.remote_address
        logger.info(f"WebChat client connected: {client_address}")
        
        # Use the client IP as their unique session_id (one session per IP)
        session_id = f"webchat_{client_address[0]}"
        self._sessions[session_id] = websocket

        try:
            async for message in websocket:
                if isinstance(message, str):
                    await self._process_text_message(message, session_id)
                elif isinstance(message, bytes):
                    # We expect JSON strings; binary frames are decoded as text
                    await self._process_text_message(message.decode("utf-8", errors="replace"), session_id)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebChat client disconnected: {client_address}")
        except Exception as e:
            logger.error(f"WebChat client error: {e}")
        finally:
            self._sessions.pop(session_id, None)

    async def _process_text_message(self, message: str, session_id: str) -> None:
        """Process an incoming message from the web UI."""
        try:
            data = json.loads(message)
            msg_type = data.get("type", "text")
            
            media_paths = []
            content = data.get("text", "")
            
            if msg_type == "file":
                # Handle file upload sent as base64
                filename = data.get("filename", f"upload_{int(time.time())}.txt")
                b64_data = data.get("data", "")
                if b64_data.startswith("data:"):
                    # Strip data URIs "data:image/png;base64,..."
                    b64_data = b64_data.split(",", 1)[-1]
                
                try:
                    file_bytes = base64.b64decode(b64_data)
                    
                    media_dir = Path.home() / ".mobot" / "media"
                    media_dir.mkdir(parents=True, exist_ok=True)
                    
                    filepath = media_dir / filename
                    filepath.write_bytes(file_bytes)
                    media_paths.append(str(filepath))
                    
                    if not content:
                        content = f"[Uploaded file: {filename}]"
                except Exception as e:
                    logger.error(f"Failed to decode webchat file upload: {e}")
                    content = f"[Failed to upload file: {filename}]"
            
            if not content and not media_paths:
                return

            await self._handle_message(
                sender_id=session_id,
                chat_id=session_id,
                content=content,
                media=media_paths,
                metadata={"source": "webchat"},
                session_key=session_id,  # Ensures outbound routing maps back to this websocket
            )
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received from webchat: {message[:50]}...")

    async def send(self, msg: OutboundMessage) -> None:
        """Send message out to the WebChat client that originated the conversation."""
        if not self._running:
            return

        # Route to the specific session that sent the original message.
        # OutboundMessage.chat_id is set to session_id from _handle_message call.
        session_id = msg.chat_id
        websocket = self._sessions.get(session_id)
        if not websocket:
            logger.debug(f"WebChat: no active session for {session_id!r}, dropping outbound message")
            return

        payload = {
            "type": "message",
            "text": msg.content,
            "media": []
        }

        if msg.media:
            for path in msg.media:
                p = Path(path)
                if p.exists():
                    try:
                        mime_type, _ = mimetypes.guess_type(path)
                        if mime_type and mime_type.startswith("image/"):
                            b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
                            payload["media"].append({
                                "filename": p.name,
                                "type": mime_type,
                                "data": f"data:{mime_type};base64,{b64}"
                            })
                        else:
                            # Non-image: mention the file in text
                            payload["text"] += f"\n[File: {p.name}]"
                    except Exception as e:
                        logger.error(f"Failed to send media via webchat: {e}")

        payload_str = json.dumps(payload)
        try:
            await websocket.send(payload_str)
        except Exception as e:
            logger.error(f"Failed to send to webchat session {session_id}: {e}")
            self._sessions.pop(session_id, None)
