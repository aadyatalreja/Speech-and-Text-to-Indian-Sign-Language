import logging
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from models.translation import TranslationRequest, TranslationResponse
from services.gloss_service import translate

log = logging.getLogger("signai.api")
router = APIRouter()

@router.post("/translate", response_model=TranslationResponse)
async def translate_endpoint(req: TranslationRequest):
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
        req = TranslationRequest(**(await ws.receive_json()))
        res = await translate(req)
        await ws.send_json({"type": "understanding", "intent": res.intent,
                            "entities": [e.model_dump() for e in res.entities],
                            "gloss": res.gloss, "confidence": res.confidence,
                            "engine": res.engine, "notice": res.notice})
        for i, item in enumerate(res.sequence):
            await ws.send_json({"type": "sign", "index": i, "item": item.model_dump()})
        await ws.send_json({"type": "done", "unknown_signs": res.unknown_signs})
    except WebSocketDisconnect:
        return
    except ValidationError:
        await ws.send_json({"type": "error", "error": "Please enter a sentence."})
    except Exception:
        log.exception("stream failed")
        await ws.send_json({"type": "error", "error": "Translation service temporarily unavailable."})
    finally:
        try:
            await ws.close()
        except Exception:
            pass
