from models.translation import TranslationRequest, TranslationResponse
from services import llm_service
from services.sequence_service import SignSequenceService

async def translate(req: TranslationRequest) -> TranslationResponse:
    result, engine, notice = await llm_service.understand(req.text)
    seq, unknown = SignSequenceService().build(result.gloss)
    if unknown:
        notice = (notice + " " if notice else "") + "Some signs are currently unavailable."
    return TranslationResponse(
        original_text=req.text, target_sign_language=req.target_sign_language,
        intent=result.intent, entities=result.entities, gloss=result.gloss,
        sequence=seq, unknown_signs=unknown, confidence=result.confidence,
        engine=engine, notice=notice)
