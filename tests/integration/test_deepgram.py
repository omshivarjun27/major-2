import asyncio
import os

import aiohttp
import pytest
from dotenv import load_dotenv

load_dotenv()

@pytest.mark.asyncio
async def test_deepgram():
    api_key = os.getenv("DEEPGRAM_API_KEY")
    print(f"Testing Deepgram API key: {api_key[:10]}...")

    # Test simple HTTP connection first
    async with aiohttp.ClientSession() as session:
        try:
            # Test basic connectivity
            print("Testing basic HTTP connectivity...")
            resp = await asyncio.wait_for(
                session.get('https://api.deepgram.com/'),
                timeout=10
            )
            print(f"HTTP Status: {resp.status}")
        except asyncio.TimeoutError:
            print("TIMEOUT: Cannot reach api.deepgram.com - network issue!")
        except Exception as e:
            print(f"Error: {type(e).__name__}: {e}")

    # Test WebSocket connection
    async with aiohttp.ClientSession() as session:
        try:
            print("\nTesting WebSocket connection...")
            ws_url = "wss://api.deepgram.com/v1/listen?encoding=linear16&sample_rate=16000"
            ws = await asyncio.wait_for(
                session.ws_connect(
                    ws_url,
                    headers={"Authorization": f"Token {api_key}"}
                ),
                timeout=10
            )
            print("WebSocket connected successfully!")
            await ws.close()
        except asyncio.TimeoutError:
            print("TIMEOUT: WebSocket connection to Deepgram failed - likely firewall/network issue!")
        except Exception as e:
            print(f"WebSocket Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_deepgram())
