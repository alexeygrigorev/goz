import asyncio
import httpx
import json
from pathlib import Path

async def test():
    config_file = Path.home() / ".config" / "goz" / "config.json"
    with open(config_file) as f:
        config = json.load(f)
    
    url = f"{config['zai_base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config['zai_token']}",
        "Content-Type": "application/json",
    }
    
    body = {
        "model": config.get('vision_model', 'glm-4.6v'),
        "messages": [{
            "role": "user", 
            "content": [
                {"type": "text", "text": "What do you see?"},
                {"type": "image_url", "image_url": {"url": "https://picsum.photos/400"}}
            ]
        }],
        "thinking": {"type": "enabled"},
        "stream": False,
        "temperature": config.get('temperature', 0.8),
        "top_p": config.get('top_p', 0.6),
        "max_tokens": config.get('max_tokens', 32768),
    }
    
    print(f"URL: {url}")
    print(f"Body: {json.dumps(body, indent=2)[:500]}")
    
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, json=body, headers=headers)
        print(f"Status: {response.status_code}")
        result = json.loads(response.text)
        print(f"Response: {json.dumps(result, indent=2)[:2000]}")

asyncio.run(test())
