# gptoss_client.py
from __future__ import annotations
import os, time
from typing import List, Dict, Any, Optional
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Point to the base server (no path). Example:
#  - Desktop via tunnel: http://127.0.0.1:8000
#  - On the server:  http://127.0.0.1:8000
#  - Remote server:  http://136.243.40.162:8000
#  - Public domain:      https://chat.anqa.cloud
BASE = os.getenv("GPT_OSS_SERVER", "http://136.243.40.162:5000").rstrip("/")

# vLLM Loader API endpoints
ENDPOINT_CHAT = f"{BASE}/chat"

TIMEOUT_S = float(os.getenv("GPT_OSS_TIMEOUT", "60"))
MODEL = os.getenv("GPT_OSS_MODEL", "openai/gpt-oss-20b")

class GPTOSSError(RuntimeError):
    pass

def _post_json(url: str, payload: Dict[str, Any], retries: int = 2) -> Dict[str, Any]:
    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            r = requests.post(url, json=payload, timeout=TIMEOUT_S)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_err = e
            time.sleep(0.75 * (attempt + 1))
    raise GPTOSSError(f"Request to {url} failed after retries: {last_err}")

def chat(prompt: str, max_tokens: int = 256, temperature: float = 0.7) -> str:
    """
    Simple text-in → text-out using vLLM Loader /chat endpoint.
    """
    payload = {
        "message": prompt,
        # Note: max_tokens and temperature may not be supported by this API
    }
    data = _post_json(ENDPOINT_CHAT, payload)
    # vLLM Loader API returns: {"response":"..."}
    try:
        response = (data["response"] or "").strip()
        
        # Handle echo responses (server in test mode)
        if response.startswith("Echo: "):
            response = response[6:]  # Remove "Echo: " prefix
            
        return response
    except Exception:
        return str(data)

def chat_messages(messages: List[Dict[str, str]], max_tokens: int = 256, temperature: float = 0.7) -> str:
    """
    Chat-style with roles - converts to simple prompt for custom API.
    messages = [{"role":"user","content":"hi"}, {"role":"assistant","content":"..."}]
    """
    # Convert messages to a simple prompt format
    prompt_parts = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            prompt_parts.append(f"User: {content}")
        elif role == "assistant":
            prompt_parts.append(f"Assistant: {content}")
        else:
            prompt_parts.append(f"{role}: {content}")
    
    prompt = "\n".join(prompt_parts) + "\nAssistant:"
    return chat(prompt, max_tokens, temperature)

def healthcheck() -> bool:
    try:
        echo = chat("ping", max_tokens=4)
        return isinstance(echo, str) and len(echo) > 0
    except Exception:
        return False
