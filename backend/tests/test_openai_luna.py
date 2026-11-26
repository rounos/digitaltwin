"""Offline contract tests for the OpenAI GPT-6 Luna configuration and transport."""
import json
from app.ai.llm_client import configured_provider, call_llm_json


def test_gpt6_luna_responses_request(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-placeholder")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-6-luna")
    captured = {}

    class StubResponse:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def read(self):
            return json.dumps({
                "status": "completed",
                "output": [
                    {"type": "reasoning", "summary": []},
                    {"type": "message", "content": [{"type": "output_text", "text": '{"twin_reply":"Μάλιστα"}'}]},
                ],
            }).encode("utf-8")

    def stub_open(req, timeout):
        captured["url"] = req.full_url
        captured["payload"] = json.loads(req.data)
        captured["timeout"] = timeout
        return StubResponse()

    monkeypatch.setattr("urllib.request.urlopen", stub_open)
    assert configured_provider() == "openai"
    assert call_llm_json("Respond JSON only", "hello") == {"twin_reply": "Μάλιστα"}
    assert captured["url"] == "https://api.openai.com/v1/responses"
    assert captured["payload"]["model"] == "gpt-6-luna"
    assert captured["payload"]["text"]["format"]["type"] == "json_object"
    assert captured["payload"]["reasoning"]["effort"] == "none"
    assert captured["payload"]["store"] is False
    assert captured["payload"]["input"][1]["content"] == "hello"


def test_selects_only_configured_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-other-provider-key")
    assert configured_provider() is None
    assert call_llm_json("system", "user") is None


def test_health_displays_openai_model(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-placeholder")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-6-luna")
    from app.main import health
    import asyncio
    result = asyncio.run(health())
    assert result["provider"] == "openai"
    assert result["model"] == "gpt-6-luna"
    assert result["llm_configured"] is True
