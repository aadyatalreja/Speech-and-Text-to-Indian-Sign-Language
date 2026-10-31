"""Numeric avatar channels; these bounds are rig limits, not ISL rules."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Angle = Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)]


class NonManualMarkers(BaseModel):
    model_config = ConfigDict(extra="forbid")
    brow: float | None = Field(default=None, ge=-1, le=1, allow_inf_nan=False)
    head: tuple[Angle, Angle, Angle] | None = None
    mouth: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)


class GlossToken(BaseModel):
    gloss: str
    nmm: NonManualMarkers = Field(default_factory=NonManualMarkers)
    fs: bool = False
    nmm_rules: list[str] = Field(default_factory=list)
    nmm_verified: bool = False
    reference: str | None = None  # reviewed rule's referent label; not a spatial pose

    @model_validator(mode="after")
    def spelling_flag(self):
        if self.fs and not self.gloss.upper().startswith("FS:"):
            self.gloss = f"FS:{self.gloss}"
        self.fs = self.gloss.upper().startswith("FS:")
        return self


class SentenceMetadata(BaseModel):
    intent: str = "statement"
    question_type: Literal["yes_no", "wh"] | None = None
    negated: bool = False
    topic: str | None = None
