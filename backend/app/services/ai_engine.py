import os
import httpx

def _get_ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "http://10.4.15.52:11434").rstrip("/")

def _get_ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

def _get_ollama_timeout() -> float:
    return float(os.getenv("OLLAMA_TIMEOUT", "300"))

async def call_ollama_chat(prompt: str) -> str:
    base_url = _get_ollama_base_url()
    url = f"{base_url}/api/chat"
    payload = {
        "model": _get_ollama_model(),
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    timeout = _get_ollama_timeout()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
            print("OLLAMA STATUS:", resp.status_code)
            print("OLLAMA RAW:", resp.text[:400])
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]
    except httpx.ReadTimeout:
        return f"[ERROR] Ollama read timeout ({int(timeout)}s) - โมเดลอาจช้ามากหรือค้าง"
    except Exception as e:
        return f"[ERROR] Ollama call failed: {e}"
