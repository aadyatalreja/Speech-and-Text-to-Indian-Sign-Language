from pydantic import BaseModel, Field, field_validator, model_validator
from .sign import SignSequenceItem
from .markers import GlossToken, SentenceMetadata
from .grammar import GrammarUse

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
    gloss: list[GlossToken] = Field(min_length=1)
    sentence: SentenceMetadata = Field(default_factory=SentenceMetadata)
    grammar_rules: list[GrammarUse] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0, le=1)

    @field_validator("gloss", mode="before")
    @classmethod
    def accept_legacy_gloss(cls, value):
        if isinstance(value, list):
            return [{"gloss": item} if isinstance(item, str) else item for item in value]
        return value

    @property
    def flat_gloss(self) -> list[str]:
        return [token.gloss for token in self.gloss]

    @model_validator(mode="after")
    def sync_sentence_intent(self):
        self.sentence.intent = self.intent
        return self

class TranslationResponse(BaseModel):
    original_text: str
    target_sign_language: str
    intent: str
    entities: list[Entity]
    gloss: list[str]
    gloss_detail: list[GlossToken] = Field(default_factory=list)
    sentence: SentenceMetadata = Field(default_factory=SentenceMetadata)
    grammar_rules: list[GrammarUse] = Field(default_factory=list)
    sequence: list[SignSequenceItem]
    unknown_signs: list[str]
    confidence: float
    engine: str  # mock | api | mock-fallback
    notice: str | None = None

class VideoRequest(BaseModel):
    sequence: list[str] = Field(min_length=1)
