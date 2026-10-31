from pydantic import BaseModel, Field, field_validator
from .sign import SignSequenceItem

class TranslationRequest(BaseModel):
    text: str = Field(max_length=500)
    source_language: str = "English"
    target_sign_language: str = "ISL"

    @field_validator("text")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Please enter a sentence.")
        return v.strip()

class Entity(BaseModel):
    text: str
    type: str

class LLMResult(BaseModel):
    intent: str = "statement"
    entities: list[Entity] = []
    gloss: list[str] = Field(min_length=1)
    confidence: float = Field(default=0.5, ge=0, le=1)

class TranslationResponse(BaseModel):
    original_text: str
    target_sign_language: str
    intent: str
    entities: list[Entity]
    gloss: list[str]
    sequence: list[SignSequenceItem]
    unknown_signs: list[str]
    confidence: float
    engine: str  # mock | api | mock-fallback
    notice: str | None = None

class VideoRequest(BaseModel):
    sequence: list[str] = Field(min_length=1)
