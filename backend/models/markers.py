"""Numeric avatar channels; these bounds are rig limits, not ISL rules."""

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator, model_serializer

Angle = Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)]


RigUnit = Annotated[float, Field(ge=-1, le=1, allow_inf_nan=False)]
ShapeUnit = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class MouthShape(BaseModel):
    model_config = ConfigDict(extra="forbid")
    open: ShapeUnit | None = None
    wide: ShapeUnit | None = None
    round: ShapeUnit | None = None


class NonManualMarkers(BaseModel):
    model_config = ConfigDict(extra="forbid")
    brow: float | None = Field(default=None, ge=-1, le=1, allow_inf_nan=False)
    head: tuple[Angle, Angle, Angle] | None = None
    mouth: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    gaze: tuple[RigUnit, RigUnit] | None = None
    mouth_shape: MouthShape | None = None

    @model_serializer(mode="wrap")
    def compatible_channels(self, handler):
        data = handler(self)
        # Keep the legacy wire/dump shape for clips with no v2 markers.
        for name in ("gaze", "mouth_shape"):
            if data.get(name) is None:
                data.pop(name, None)
        return data


class GlossToken(BaseModel):
    gloss: str
    nmm: NonManualMarkers = Field(default_factory=NonManualMarkers)
    fs: bool = False
    fs_reason: Literal["oov", "name_heuristic", "model_unknown", "explicit"] | None = None
    lemma_tried: str | None = None
    synonym_from: str | None = None  # English lexical substitution, never an ISL claim
    nmm_rules: list[str] = Field(default_factory=list)
    nmm_verified: bool = False
    reference: str | None = None  # reviewed rule's referent label; not a spatial pose

    @model_validator(mode="after")
    def spelling_flag(self):
        if self.fs and not self.gloss.upper().startswith("FS:"):
            self.gloss = f"FS:{self.gloss}"
        self.fs = self.gloss.upper().startswith("FS:")
        if self.fs and self.fs_reason is None:
            self.fs_reason = "explicit"
        return self


class SentenceMetadata(BaseModel):
    intent: str = "statement"
    question_type: Literal["yes_no", "wh"] | None = None
    negated: bool = False
    topic: str | None = None
