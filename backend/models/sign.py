from typing import Literal
from pydantic import BaseModel, Field
from .markers import NonManualMarkers

class ClipQA(BaseModel):
    both_hands_fraction: float = Field(ge=0, le=1)
    left_hand_fraction: float = Field(ge=0, le=1)
    right_hand_fraction: float = Field(ge=0, le=1)
    pose_fraction: float = Field(ge=0, le=1)
    jitter: float = Field(ge=0, allow_inf_nan=False)
    frame_count: int = Field(ge=2)
    key_count: int = Field(ge=2)
    duration: float = Field(gt=0, allow_inf_nan=False)
    score: float = Field(ge=0, le=1)
    method: str = "heuristic-v1; not ISL validation"

class Sign(BaseModel):
    id: str
    gloss: str
    aliases: list[str] = Field(default_factory=list)
    lemma: str | None = None
    category: str | None = None
    asset_type: Literal["demo", "dataset", "video"] = "demo"
    video: str | None = None
    keypoints: str | None = None
    clip: str | None = None  # avatar clip JSON, relative to the signs folder (see frontend/src/avatar/types.ts)
    source: str | None = None
    licence: str | None = None
    signer: str | None = None
    review_status: Literal["unverified", "in_review", "verified"] = "unverified"
    notes: str | None = None
    qa: ClipQA | None = None
    needs_manual_review: bool = True
    duration: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    import_fingerprint: str | None = None
    import_files: dict[str, str] = Field(default_factory=dict)
    video_duration: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    reviewer: str | None = None
    review_decision: Literal["verified", "rejected"] | None = None
    clip_review_decision: Literal["verified", "rejected"] | None = None
    review_history: list[dict] = Field(default_factory=list)

class SignSequenceItem(BaseModel):
    gloss: str
    sign_id: str | None
    available: bool
    duration: float
    pause_after: float = 0.2
    asset_type: str = "demo"
    video_url: str | None = None
    clip_url: str | None = None
    nmm: NonManualMarkers = Field(default_factory=NonManualMarkers)
    nmm_rules: list[str] = Field(default_factory=list)
    nmm_verified: bool = False
    reference: str | None = None
    source: str | None = None
    licence: str | None = None
    signer: str | None = None
    review_status: Literal["unverified", "in_review", "verified"] = "unverified"
    needs_manual_review: bool = True
    sequence_index: int = 0
    timing_source: Literal["clip", "video", "spelling_estimate", "demo_estimate"] = "demo_estimate"
    clip_duration: float | None = None
    video_duration: float | None = None
    transition_duration: float = 0.18
