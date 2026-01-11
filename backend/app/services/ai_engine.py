import httpx
from ..core.settings import settings

def _get_ollama_chat_url() -> str:
    return f"{settings.AI_MODEL_ENDPOINT}/api/chat"

async def call_ollama_chat(prompt: str) -> str:
    url = _get_ollama_chat_url()

    payload = {
        "model": settings.AI_MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "stream": False,
    }

    try:
        # timeout = 600 วินาที (10 นาที)
        async with httpx.AsyncClient(timeout=600) as client:
            resp = await client.post(url, json=payload)
            print("OLLAMA STATUS:", resp.status_code)
            print("OLLAMA RAW:", resp.text[:400])
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]
    except httpx.ReadTimeout:
        return "[ERROR] Ollama read timeout (600s) - โมเดลอาจช้ามากหรือค้าง"
    except Exception as e:
        return f"[ERROR] Ollama call failed: {e}"
