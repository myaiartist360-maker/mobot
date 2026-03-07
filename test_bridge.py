import asyncio
import websockets
import json

async def test():
    print("Testing websocket bridge connections...")
    try:
        async with websockets.connect('ws://127.0.0.1:3001') as ws:
            print('Connected to bridge! Waiting for msgs...')
            while True:
                msg = await ws.recv()
                print('GOT', msg)
    except Exception as e:
        print('Error:', e)
            
if __name__ == "__main__":
    asyncio.run(test())
