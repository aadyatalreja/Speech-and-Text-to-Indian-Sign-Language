"""Experimental opt-in reports. No account, IP, or automatic asset edits."""

import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
from threading import Lock

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from config import settings
from services.rate_limit import check_rate

router = APIRouter()
_lock = Lock()


class Feedback(BaseModel):
    model_config = ConfigDict(extra="forbid")
    gloss: str = Field(min_length=1, max_length=64)
    sign_id: str | None = Field(default=None, max_length=128)
    sentence: str = Field(max_length=500)
    note: str = Field(default="", max_length=300)
    timestamp: datetime


def append_report(report):
    data = (json.dumps(report.model_dump(mode="json"), ensure_ascii=False) + "\n").encode("utf-8")
    if len(data) > settings.FEEDBACK_MAX_BYTES:
        raise HTTPException(507, "Feedback storage is full; contact the reviewer.")
    path = Path(settings.FEEDBACK_PATH)
    with _lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Lock the report itself across worker processes; no sidecar file or IP is written.
        with path.open("a+b") as stream:
            if os.name == "nt":
                import msvcrt

                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                stream.seek(0, os.SEEK_END)
                if stream.tell() + len(data) > settings.FEEDBACK_MAX_BYTES:
                    raise HTTPException(507, "Feedback storage is full; contact the reviewer.")
                stream.write(data)
                stream.flush()
            finally:
                stream.seek(0)
                if os.name == "nt":
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


@router.post("/feedback", status_code=204)
async def feedback(report: Feedback, request: Request):
    check_rate(request, "feedback", settings.RATE_LIMIT_FEEDBACK_PER_MIN)
    await asyncio.to_thread(append_report, report)
    return Response(status_code=204)
