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
    url = "https://api.anthropic.com/v1/messages"
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
    except urllib.error.HTTPError as e:
        print(f"[ANTHROPIC HTTP ERROR] {e.code}: {e.read().decode('utf-8', errors='replace')}", flush=True)
        return None
    except Exception as e:
        print(f"[ANTHROPIC ERROR] {e}", flush=True)
        return None


_RETRYABLE_CODES = {429, 500, 503, 504}


def _call_gemini(api_key: str, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
    """Χρησιμοποιεί το google-genai SDK μέσω gemini_client.
    Σε προσωρινά σφάλματα (503 υπερφόρτωση, 429 όριο ρυθμού, 5xx) ξαναδοκιμάζει με αναμονή."""
    import time
    from google.genai import errors, types
    from .gemini_client import get_gemini_client

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    max_attempts = int(os.getenv("GEMINI_MAX_ATTEMPTS", "4"))
    delays = [3, 8, 15]  # δευτερόλεπτα πριν από την 2η, 3η, 4η προσπάθεια

    for attempt in range(1, max_attempts + 1):
        try:
            client = get_gemini_client()
            response = client.models.generate_content(
                model=model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.2,
                    response_mime_type="application/json",
                ),
            )
            return _parse_json_safe(response.text or "")
        except errors.APIError as e:
            retryable = getattr(e, "code", None) in _RETRYABLE_CODES
            if retryable and attempt < max_attempts:
                wait = delays[min(attempt - 1, len(delays) - 1)]
                print(f"[GEMINI RETRY] {e.code} - προσπάθεια {attempt}/{max_attempts}, νέα προσπάθεια σε {wait}s", flush=True)
                time.sleep(wait)
                continue
            print(f"[GEMINI ERROR] {type(e).__name__}: {e}", flush=True)
            return None
        except Exception as e:
            print(f"[GEMINI ERROR] {type(e).__name__}: {e}", flush=True)
            return None
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
            return _parse_json_safe(text)
    except urllib.error.HTTPError as e:
        print(f"[OPENAI HTTP ERROR] {e.code}: {e.read().decode('utf-8', errors='replace')}", flush=True)
        return None
    except Exception as e:
        print(f"[OPENAI ERROR] {e}", flush=True)
        return None