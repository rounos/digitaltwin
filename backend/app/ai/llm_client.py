import os
import re
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional


def call_llm_json(system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
    """
    Καλεί το διαθέσιμο LLM (Anthropic Claude, Gemini ή OpenAI βάσει .env) και επιστρέφει parsed JSON.
    Αν δεν υπάρχει API key ή αποτύχει η κλήση, επιστρέφει None ώστε να αναλάβει το fallback.
    """
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if anthropic_key:
        return _call_anthropic(anthropic_key, system_prompt, user_prompt)
    if gemini_key:
        return _call_gemini(gemini_key, system_prompt, user_prompt)
    if openai_key:
        return _call_openai(openai_key, system_prompt, user_prompt)
    return None


def _parse_json_safe(text: str) -> Optional[Dict[str, Any]]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.DOTALL).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
        return None


def _call_anthropic(api_key: str, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
    model = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-5")
    url = "[https://api.anthropic.com/v1/messages](https://api.anthropic.com/v1/messages)"
    payload = {
        "model": model,
        "max_tokens": 1024,
        "temperature": 0.2,
        "system": f"{system_prompt}\n\nIMPORTANT: Respond ONLY with valid raw JSON. Do not include markdown fences or extra commentary.",
        "messages": [
            {"role": "user", "content": user_prompt},
        ],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            text = body["content"][0]["text"]
            return _parse_json_safe(text)
    except (urllib.error.URLError, KeyError, IndexError, TimeoutError):
        return None


def _call_gemini(api_key: str, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    url = f"[https://generativelanguage.googleapis.com/v1beta/models/](https://generativelanguage.googleapis.com/v1beta/models/){model}:generateContent?key={api_key}"
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
            return _parse_json_safe(text)
    except (urllib.error.URLError, KeyError, TimeoutError):
        return None


def _call_openai(api_key: str, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    url = "[https://api.openai.com/v1/chat/completions](https://api.openai.com/v1/chat/completions)"
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
            return _parse_json_safe(text)
    except (urllib.error.URLError, KeyError, TimeoutError):
        return None