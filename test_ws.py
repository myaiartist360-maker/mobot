import asyncio
import http
import websockets
from websockets.server import serve

async def process_request(connection, request):
    if request.path == "/":
        return connection.respond(http.HTTPStatus.OK, b"HTML\n")
    return None

async def handler(websocket):
    pass

async def main():
    async with serve(handler, "localhost", 7899, process_request=process_request):
        print("Running...")
        await asyncio.sleep(2)

asyncio.run(main())
