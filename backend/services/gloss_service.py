import asyncio
from models.translation import TranslationRequest, TranslationResponse
from services import llm_service
from services.sequence_service import SignSequenceService
from services.marker_service import apply_markers
from services.isign import retrieve_isign


async def translate(req: TranslationRequest) -> TranslationResponse:
    if match := await retrieve_isign(req):
        return match
    english, input_notice = await llm_service.english_input(req.text, req.source_language)
    result, engine, notice = await llm_service.understand(english)
    notice = " ".join(filter(None, [input_notice, notice])) or None
    result, marker_notice = apply_markers(result, english)
    if marker_notice:
        notice = (notice + " " if notice else "") + marker_notice
    seq, unknown = await asyncio.to_thread(SignSequenceService().build, result.gloss)
    if unknown:
        notice = (
            (notice + " " if notice else "")
            + "The avatar uses labeled fingerspelling for words without a playable sign. Digits can use avatar digit poses."
        )
    return TranslationResponse(
        original_text=req.text,
        english_text=english,
        target_sign_language=req.target_sign_language,
        intent=result.intent,
        entities=result.entities,
        gloss=result.flat_gloss,
        gloss_detail=result.gloss,
        sentence=result.sentence,
        grammar_rules=result.grammar_rules,
        sequence=seq,
        unknown_signs=unknown,
        confidence=result.confidence,
        engine=engine,
        notice=notice,
    )
