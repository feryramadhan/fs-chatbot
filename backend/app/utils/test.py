import asyncio
import aiohttp
import json

async def connect():
    uri = "ws://127.0.0.1:8000/ws/bedrock-agent"

    headers = {
        "access_token": "test-token123"
    }

    try:
        # Create WebSocket connection using aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(uri, headers=headers) as websocket:
                
                message = {
                    "content": "Hi, how are you?"
                }

                await websocket.send_str(json.dumps(message))
                print("Sent message to server ....")

                # Receive message from server
                response = await websocket.receive()
                print(f"Response from server: {response.data}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(connect())