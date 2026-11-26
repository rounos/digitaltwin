import os
import re
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional


def configured_provider() -> str | None:
    """Return selected provider only when that provider has a credential."""
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    keys = {
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
    }
    if provider not in keys:
        return None
    return provider if os.getenv(keys[provider], "").strip() else None


def call_llm_json(system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
    """Invoke the explicitly configured provider; no silent switch to other keys."""
    provider = configured_provider()
    if provider == "openai":
        return _call_openai(os.environ["OPENAI_API_KEY"], system_prompt, user_prompt)
    if provider == "gemini":
        return _call_gemini(os.environ["GEMINI_API_KEY"], system_prompt, user_prompt)
    if provider == "anthropic":
        return _call_anthropic(os.environ["ANTHROPIC_API_KEY"], system_prompt, user_prompt)
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
    """GPT-6 Luna via OpenAI Responses API; returns parsed JSON without storing replies server-side."""
    model = os.getenv("OPENAI_MODEL", "gpt-6-luna")
    url = "https://api.openai.com/v1/responses"
    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": system_prompt + "\nReturn a single valid JSON object."},
            {"role": "user", "content": user_prompt},
        ],
        "reasoning": {"effort": os.getenv("OPENAI_REASONING_EFFORT", "none")},
        "max_output_tokens": int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "8192")),
        "text": {"format": {"type": "json_object"}},
        "store": False,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        if body.get("status") not in (None, "completed"):
            print(f"[OPENAI] Response status: {body.get('status')}", flush=True)
            return None
        for output in body.get("output", []):
            if output.get("type") == "message":
                for content in output.get("content", []):
                    if content.get("type") == "output_text":
                        obj = _parse_json_safe(content.get("text", ""))
                        if isinstance(obj, dict):
                            return obj
        print("[OPENAI] No JSON text found in the Responses API result", flush=True)
        return None
    except urllib.error.HTTPError as exc:
        # Do not print request data, Authorization header or the user-supplied key.
        print(f"[OPENAI] HTTP {exc.code}; check key, model access, quota and project billing", flush=True)
        return None
    except Exception as exc:
        print(f"[OPENAI] Request failed ({type(exc).__name__}); check network and backend logs", flush=True)
        return None
