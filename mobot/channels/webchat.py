"""Remote Web Chat channel implementation over WebSockets."""

import asyncio
import http
import json
import base64
import time
import mimetypes
from pathlib import Path

from loguru import logger
import websockets
from websockets.server import serve

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
        self._clients: set[websockets.WebSocketServerProtocol] = set()
        
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
        for client in list(self._clients):
            await client.close()
        self._clients.clear()

    async def _process_http_request(self, connection, request):
        """Serve the HTML UI on HTTP GET /."""
        if request.path == "/":
            return connection.respond(
                http.HTTPStatus.OK,
                self._ui_html
            )
        # For WebSocket upgrade, return None
        return None

    async def _handle_ws_connection(self, websocket):
        """Handle incoming WebSocket connection from the Web UI."""
        self._clients.add(websocket)
        client_address = websocket.remote_address
        logger.info(f"WebChat client connected: {client_address}")
        
        # We can use the client IP as their unique chat_id/sender_id
        session_id = f"webchat_{client_address[0]}"

        try:
            async for message in websocket:
                if isinstance(message, str):
                    await self._process_text_message(message, session_id)
                elif isinstance(message, bytes):
                    pass # We expect JSON strings for both text and file uploads mapped as JSON
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebChat client disconnected: {client_address}")
        except Exception as e:
            logger.error(f"WebChat client error: {e}")
        finally:
            self._clients.discard(websocket)

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
                metadata={"source": "webchat"}
            )
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received from webchat: {message[:50]}...")

    async def send(self, msg: OutboundMessage) -> None:
        """Send message out to WebChat clients."""
        if not self._running or not self._clients:
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
                            # Non-image, just send the path as text
                            payload["text"] += f"\n[File: {p.name}]"
                    except Exception as e:
                        logger.error(f"Failed to send media via webchat: {e}")

        payload_str = json.dumps(payload)
        
        for client in self._clients:
            try:
                await client.send(payload_str)
            except Exception as e:
                logger.error(f"Failed to send to webchat client: {e}")
