from pydantic import BaseModel, Field


class WritingStyle(BaseModel):
    tone: str = ""
    vocabulary_notes: str = ""


class PersonaModel(BaseModel):
    persona_id: str = "uninitialized"
    persona_version: int = 0
    name: str
    role: str
    writing_style: WritingStyle
    decision_heuristics: list[str] = Field(default_factory=list)
    knowledge_facts: list[str] = Field(default_factory=list)
    preferences: list[str] = Field(default_factory=list)
    source_stats: dict[str, int] = Field(default_factory=dict)
    evidence: list[dict] = Field(default_factory=list)


class TwinRespondRequest(BaseModel):
    incoming_message: str = Field(..., min_length=1, max_length=20000)


class TwinExplanation(BaseModel):
    applied_rules: list[str] = Field(default_factory=list)
    retrieved_memories: list[str] = Field(default_factory=list)
    style_notes: str = ""


class TwinDraftResponse(BaseModel):
    draft_id: int
    status: str
    twin_reply: str
    confidence_score: float = Field(ge=0, le=1)
    is_uncertain: bool
    explanation: TwinExplanation
