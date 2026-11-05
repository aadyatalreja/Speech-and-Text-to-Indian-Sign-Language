import logging
import asyncio
from services import llm_service
from services.marker_service import apply_markers
from services.sequence_service import SignSequenceService
from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from config import settings
from services.rate_limit import check_rate
from pydantic import ValidationError
from models.translation import TranslationRequest, TranslationResponse
from services.gloss_service import translate

log = logging.getLogger("signai.api")
router = APIRouter()


@router.post("/translate", response_model=TranslationResponse)
async def translate_endpoint(req: TranslationRequest, request: Request):
    check_rate(request, "translate", settings.RATE_LIMIT_TRANSLATE_PER_MIN)
    try:
        return await translate(req)
    except Exception:
        log.exception("translate failed")
        raise HTTPException(500, "Translation service temporarily unavailable.")


@router.websocket("/translate/stream")
async def stream(ws: WebSocket):
    """Sends 'understanding', then one 'sign' per sign, then 'done'."""
    await ws.accept()
    try:
        check_rate(ws, "translate", settings.RATE_LIMIT_TRANSLATE_PER_MIN)
    except HTTPException as exc:
        await ws.send_json(
            {"type": "error", "error": f"{exc.detail} Retry-After: {exc.headers['Retry-After']}"}
        )
        await ws.close(code=1008)
        return
    try:
        req = TranslationRequest(**(await ws.receive_json()))
        english, input_notice = await llm_service.english_input(req.text, req.source_language)
        res, engine, notice = await llm_service.understand(english)
        notice = " ".join(filter(None, [input_notice, notice])) or None
        res, marker_notice = apply_markers(res, english)
        notice = " ".join(filter(None, [notice, marker_notice])) or None
        if any(token.gloss.startswith("FS:") for token in res.gloss):
            notice = (
                (notice + " " if notice else "")
                + "Unknown words use FS: character spelling. Character playback depends on available clips and avatar poses."
            )
        await ws.send_json(
            {
                "type": "understanding",
                "english_text": english,
                "intent": res.intent,
                "entities": [e.model_dump() for e in res.entities],
                "gloss": res.flat_gloss,
                "confidence": res.confidence,
                "gloss_detail": [token.model_dump() for token in res.gloss],
                "sentence": res.sentence.model_dump(),
                "grammar_rules": [rule.model_dump() for rule in res.grammar_rules],
                "engine": engine,
                "notice": notice,
            }
        )
        service = SignSequenceService()
        unknown = []
        for i, token in enumerate(res.gloss):
            items, missing = await asyncio.to_thread(service.build, [token])
            item = items[0]
            item.sequence_index = i
            if i < len(res.gloss) - 1:
                item.pause_after = settings.INTER_SIGN_PAUSE
            unknown.extend(missing)
            await ws.send_json({"type": "sign", "index": i, "item": item.model_dump()})
        await ws.send_json({"type": "done", "unknown_signs": unknown})
    except WebSocketDisconnect:
        return
    except ValidationError:
        await ws.send_json({"type": "error", "error": "Please enter a sentence."})
    except Exception:
        log.exception("stream failed")
        await ws.send_json(
            {"type": "error", "error": "Translation service temporarily unavailable."}
        )
    finally:
        try:
            await ws.close()
        except Exception:
            pass
