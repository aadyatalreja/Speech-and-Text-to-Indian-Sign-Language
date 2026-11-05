"""Opt-in client for an authenticated private iSign worker."""

import asyncio
import json
import logging
import math
import os
import re
import unicodedata
from urllib.parse import urlsplit

import httpx

from models.sign import SignSequenceItem
from models.translation import TranslationResponse

log = logging.getLogger(__name__)
MAX_RESPONSE = 2 * 1024 * 1024


def sentence_key(text):
    text = unicodedata.normalize("NFKC", text).casefold().replace("’", "'")
    return " ".join(text.split()).rstrip(".!").strip()


def result_from_match(req, match):
    uid, clip = match["uid"], match["clip"]
    duration = clip["duration"]
    keys = clip["keys"]
    if (
        not re.fullmatch(r"[A-Za-z0-9_-]+-[0-9]+", uid)
        or clip["version"] != 2
        or clip["kind"] != "dataset"
        or clip["id"] != uid
        or not math.isfinite(duration)
        or not 0 < duration <= 45
        or not isinstance(keys, list)
        or not 2 <= len(keys) <= 360
    ):
        raise ValueError("Invalid worker clip")
    times = [key["t"] for key in keys]
    if times != sorted(times) or not all(math.isfinite(t) and 0 <= t <= 1 for t in times):
        raise ValueError("Invalid worker timing")
    label = "ISIGN_SEQUENCE"
    item = SignSequenceItem(
        gloss=label,
        sign_id=uid,
        available=True,
        duration=duration,
        pause_after=0,
        asset_type="dataset",
        inline_clip=clip,
        clip_duration=duration,
        timing_source="clip",
        source="Exploration-Lab/iSign",
    )
    return TranslationResponse(
        original_text=req.text,
        english_text=req.text,
        target_sign_language="ISL",
        intent="retrieved sequence",
        entities=[],
        gloss=[label],
        sequence=[item],
        unknown_signs=[],
        confidence=1,
        engine="isign-exact",
        notice=f"Exact transcript match · iSign UID {uid} · avatar retargeting pending signer review.",
    )


async def retrieve_isign(req):
    url = os.environ.get("SIGN_AI_ISIGN_URL", "")
    token = os.environ.get("SIGN_AI_ISIGN_TOKEN", "")
    if (
        not url
        or len(token) < 32
        or req.target_sign_language.casefold() != "isl"
        or req.source_language.casefold() not in {"english", "en", "en-in", "en-us", "en-gb"}
    ):
        return None
    try:
        endpoint = urlsplit(url)
        if endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
            raise ValueError("Invalid worker URL")
        if not endpoint.hostname or (
            endpoint.scheme != "https"
            and not (
                endpoint.scheme == "http" and endpoint.hostname in {"localhost", "127.0.0.1", "::1"}
            )
        ):
            raise ValueError("Worker URL requires HTTPS or a loopback tunnel")
        async with asyncio.timeout(12), httpx.AsyncClient(timeout=10, trust_env=False) as client:
            async with client.stream(
                "POST",
                url.rstrip("/") + "/retrieve",
                json=req.model_dump(),
                headers={"Authorization": f"Bearer {token}"},
            ) as response:
                response.raise_for_status()
                payload = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(payload) + len(chunk) > MAX_RESPONSE:
                        raise ValueError("Worker response exceeds size limit")
                    payload.extend(chunk)
        match = json.loads(payload)["match"]
        return result_from_match(req, match) if match is not None else None
    except (httpx.HTTPError, TimeoutError, ValueError, TypeError, KeyError, AttributeError):
        log.warning("Private iSign lookup unavailable")
        return None
