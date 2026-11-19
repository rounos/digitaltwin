import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional


def call_llm_json(system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
    """
    Καλεί το διαθέσιμο LLM (Gemini ή OpenAI βάσει .env) και επιστρέφει parsed JSON.
    Αν δεν υπάρχει API key ή αποτύχει η κλήση, επιστρέφει None ώστε να αναλάβει το fallback.
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if gemini_key:
        return _call_gemini(gemini_key, system_prompt, user_prompt)
    if openai_key:
        return _call_openai(openai_key, system_prompt, user_prompt)
    return None


def _call_gemini(api_key: str, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            text = body["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
    except (urllib.error.URLError, KeyError, json.JSONDecodeError, TimeoutError):
        return None


def _call_openai(api_key: str, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            text = body["choices"][0]["message"]["content"]
            return json.loads(text)
    except (urllib.error.URLError, KeyError, json.JSONDecodeError, TimeoutError):
        return None