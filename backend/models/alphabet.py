"""Alphabet asset records; missing clips never imply known ISL handshapes."""
import re
import string
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AlphabetEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    clip: str | None
    source: str | None
    licence: str | None
    signer: str | None
    review_status: Literal["unverified", "in_review", "verified"]
    duration: float | None = Field(default=None, gt=0, le=30, allow_inf_nan=False)
    notes: str
    reviewer: str | None = None
    review_decision: Literal["verified", "rejected"] | None = None
    review_history: list[dict] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_asset(self):
        if self.clip is None:
            if self.review_status != "unverified":
                raise ValueError("Missing alphabet clips must remain unverified")
        else:
            if not re.fullmatch(r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*\.json", self.clip):
                raise ValueError("Alphabet clip must be a relative JSON path inside alphabet/")
            if not all((value or "").strip() for value in (self.source, self.licence, self.signer)):
                raise ValueError("Alphabet clips require source, licence, and signer")
            if self.duration is None:
                raise ValueError("Alphabet clips require duration in seconds")
        return self


class AlphabetManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1]
    characters: dict[str, AlphabetEntry]

    @model_validator(mode="after")
    def character_set(self):
        if set(self.characters) != set(string.ascii_uppercase + string.digits):
            raise ValueError("Alphabet manifest must contain exactly A-Z and 0-9")
        clips = [entry.clip for entry in self.characters.values() if entry.clip]
        if len(set(clips)) != len(clips):
            raise ValueError("Alphabet characters must have distinct clip files")
        return self
