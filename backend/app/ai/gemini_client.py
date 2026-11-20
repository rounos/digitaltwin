import os
from google import genai


def get_gemini_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("Λείπει το GEMINI_API_KEY από το .env")

    # Το Google AI Studio δίνει πλέον keys με πρόθεμα "AQ." και για το κανονικό
    # (δωρεάν) Gemini API, οπότε το πρόθεμα ΔΕΝ δείχνει Vertex AI.
    # Το Vertex AI Express ενεργοποιείται μόνο ρητά, με GEMINI_USE_VERTEX=true.
    if os.getenv("GEMINI_USE_VERTEX", "false").lower() in ("1", "true", "yes"):
        return genai.Client(vertexai=True, api_key=api_key)
    return genai.Client(api_key=api_key)


def ask_gemini(prompt: str, system_instruction: str | None = None) -> str:
    client = get_gemini_client()
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    config = {"system_instruction": system_instruction} if system_instruction else None
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=config,
    )
    return response.text or ""