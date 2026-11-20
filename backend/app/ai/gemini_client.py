import os
from google import genai


def get_gemini_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("Λείπει το GEMINI_API_KEY από το .env")

    # Τα keys που ξεκινούν με AQ. χρησιμοποιούν το Vertex AI Express endpoint
    if api_key.startswith("AQ."):
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