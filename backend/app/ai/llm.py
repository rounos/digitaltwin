from __future__ import annotations

import json
from typing import Type, TypeVar
from pydantic import BaseModel

from app.ai.llm_client import call_llm_json
from app.config import Settings, get_settings

T = TypeVar("T", bound=BaseModel)


class StructuredLLM:
    def __init__(self, settings: Settings):
        self.settings = settings

    def parse(self, system_prompt: str, user_prompt: str, schema: Type[T]) -> T:
        schema_hint = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        full_system = (
            f"{system_prompt}\n\n"
            f"Return ONLY valid JSON matching this schema:\n{schema_hint}"
        )
        raw = call_llm_json(full_system, user_prompt)
        if not raw:
            # Επιστρέφει κενό valid αντικείμενο του schema αν αποτύχει η κλήση
            return schema.model_validate({
                k: [] for k in schema.model_fields.keys()
            })
        return schema.model_validate(raw)


def get_llm(settings: Settings | None = None) -> StructuredLLM | None:
    s = settings or get_settings()
    if s.gemini_api_key or s.openai_api_key:
        return StructuredLLM(s)
    return None