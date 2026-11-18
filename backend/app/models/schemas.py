from pydantic import BaseModel, Field
from typing import List, Optional


class WritingStyle(BaseModel):
    tone: str
    vocabulary_notes: str


class PersonaModel(BaseModel):
    persona_id: str = "default_user"
    name: str
    role: str
    writing_style: WritingStyle
    decision_heuristics: List[str] = Field(default_factory=list)
    knowledge_facts: List[str] = Field(default_factory=list)


class TwinRespondRequest(BaseModel):
    incoming_message: str = Field(..., min_length=1)


class TwinExplanation(BaseModel):
    applied_rules: List[str] = Field(default_factory=list)
    retrieved_memories: List[str] = Field(default_factory=list)
    style_notes: str


class TwinDraftResponse(BaseModel):
    draft_id: int
    status: str
    twin_reply: str
    confidence_score: float
    is_uncertain: bool
    explanation: TwinExplanation