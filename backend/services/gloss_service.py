from models.translation import TranslationRequest, TranslationResponse
from services import llm_service
from services.sequence_service import SignSequenceService
from services.marker_service import apply_markers

async def translate(req: TranslationRequest) -> TranslationResponse:
    result, engine, notice = await llm_service.understand(req.text)
    result, marker_notice = apply_markers(result, req.text)
    if marker_notice:
        notice = (notice + " " if notice else "") + marker_notice
    seq, unknown = SignSequenceService().build(result.gloss)
    if unknown:
        notice = (notice + " " if notice else "") + "Unknown words are marked FS: for character spelling. Missing letters use placeholder fingerspelling (not the ISL alphabet); missing digits are shown as text."
    return TranslationResponse(
        original_text=req.text, target_sign_language=req.target_sign_language,
        intent=result.intent, entities=result.entities, gloss=result.flat_gloss,
        gloss_detail=result.gloss, sentence=result.sentence,
        grammar_rules=result.grammar_rules,
        sequence=seq, unknown_signs=unknown, confidence=result.confidence,
        engine=engine, notice=notice)
