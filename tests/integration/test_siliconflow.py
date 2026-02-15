"""Test SiliconFlow API connectivity"""
import os
import asyncio
import pytest
from dotenv import load_dotenv
import openai

load_dotenv()

@pytest.mark.asyncio
async def test_siliconflow():
    api_key = os.getenv("OLLAMA_VL_API_KEY")
    model = os.getenv("OLLAMA_VL_MODEL_ID", "Qwen/Qwen3-VL-235B-Instruct")
    base_url = "https://api.siliconflow.cn/v1"
    
    print(f"API Key: {api_key[:20]}..." if api_key else "No API key!")
    print(f"Model: {model}")
    print(f"Base URL: {base_url}")
    
    client = openai.AsyncOpenAI(
        api_key=api_key,
        base_url=base_url
    )
    
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hello, say hi back in one word."}],
            max_tokens=10
        )
        print(f"Response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_siliconflow())
