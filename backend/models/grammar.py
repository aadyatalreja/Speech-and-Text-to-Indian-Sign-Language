from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class GrammarRule(BaseModel):
    """Executable operations only acquire linguistic meaning from reviewed data."""
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    review_status: Literal["unverified", "in_review", "verified"] = "unverified"
    reviewer: str | None = None
    enabled: bool = False
    operation: Literal["drop_words", "phrase", "order_categories", "move_category",
                       "topic_first", "repeat", "pronoun_index", "pending"]
    words: list[str] = Field(default_factory=list)
    english: str | None = None
    gloss: list[str] = Field(default_factory=list)
    intent: str | None = None
    categories: list[str] = Field(default_factory=list)
    category: str | None = None
    position: Literal["start", "end"] = "end"
    count: int = Field(default=1, ge=1, le=3)
    references: dict[str, str] = Field(default_factory=dict)
    when_words: list[str] = Field(default_factory=list)
    notes: str | None = None
    review_decision: Literal["verified", "rejected"] | None = None
    review_history: list[dict] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_operation(self):
        if not self.id.strip() or not self.source.strip():
            raise ValueError("Rule id and source must not be blank")
        if self.review_status == "verified" and not (self.reviewer or "").strip():
            raise ValueError("Verified grammar rules require a reviewer")
        if self.enabled:
            if self.operation == "pending":
                raise ValueError("Pending linguistic rules cannot be enabled")
            if self.operation == "drop_words" and not self.words:
                raise ValueError("drop_words requires words")
            if self.operation == "phrase" and (not self.english or not self.gloss):
                raise ValueError("phrase requires english and gloss")
            if self.operation == "order_categories" and (
                self.categories.count("rest") != 1 or len(set(self.categories)) != len(self.categories)):
                raise ValueError("order_categories requires unique categories including rest")
            if self.operation in {"move_category", "repeat"} and not self.category:
                raise ValueError("Category operation requires category")
            if self.operation == "pronoun_index" and not self.references:
                raise ValueError("pronoun_index requires explicit references")
        return self


class GrammarUse(BaseModel):
    id: str
    source: str
    review_status: Literal["unverified", "in_review", "verified"]
    reviewer: str | None = None
