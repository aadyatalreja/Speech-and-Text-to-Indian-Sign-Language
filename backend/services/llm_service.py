import json, logging, re
import httpx
from config import settings
from models.translation import LLMResult, Entity

log = logging.getLogger("signai.llm")

SYSTEM_PROMPT = """You are the linguistic processing component of an AI-powered
Text-to-Indian-Sign-Language translation system.
You receive natural-language English. Understand the meaning and transform the
sentence into an intermediate representation suitable for sign-language generation.
Do NOT perform a literal word-by-word translation.
Analyze: semantic meaning, subject, action, object, time, location, negation,
question type, entities, context.
Generate an ordered gloss sequence (UPPERCASE, underscores for multiword).
Target sign language: {target}
Rules: preserve meaning; do not invent signs or sign IDs; return only valid JSON
like {{"intent":"statement|question|request|greeting","entities":[{{"text":"","type":""}}],"gloss":["..."],"confidence":0.0}}.
This gloss is a computational intermediate representation, not an authoritative linguistic translation."""

class LLMError(Exception): ...

MOCK = {
    "hello": ("greeting", ["HELLO"]),
    "thank you": ("greeting", ["THANK_YOU"]),
    "i am going to school": ("statement", ["I", "SCHOOL", "GO"]),
    "i need help": ("request", ["I", "HELP", "NEED"]),
    "where is the hospital": ("question", ["HOSPITAL", "WHERE"]),
    "can you help me": ("question", ["YOU", "HELP", "ME"]),
    "see you tomorrow": ("statement", ["TOMORROW", "SEE", "YOU"]),
}
STOP = {"am","is","are","the","a","an","to","do","does","will","be","of","can","could","please"}
TIME = {"TOMORROW","TODAY","YESTERDAY"}
QWORDS = {"WHAT","WHERE","WHEN","WHY","HOW"}
VERBS = {"going":"GO","go":"GO","come":"COME","coming":"COME","eat":"EAT","drink":"DRINK",
         "help":"HELP","need":"NEED","want":"WANT","see":"SEE","understand":"UNDERSTAND"}
ENT = {"college":"LOCATION","school":"LOCATION","hospital":"LOCATION","home":"LOCATION","water":"OBJECT"}

def mock_transform(text: str) -> LLMResult:
    """Deterministic rules: exact phrases, else time -> objects -> verb -> negation -> question word."""
    clean = re.sub(r"[^\w\s']", "", text.lower()).strip()
    if clean in MOCK:
        intent, gloss = MOCK[clean]
        conf = 0.95
    else:
        words = clean.replace("don't", "do not").split()
        negated = "not" in words
        toks = [VERBS.get(w, w.upper()) for w in words if w not in STOP and w != "not"]
        verbs = [t for t in toks if t in set(VERBS.values())]
        time = [t for t in toks if t in TIME]
        q = [t for t in toks if t in QWORDS]
        rest = [t for t in toks if t not in TIME and t not in QWORDS and t not in verbs]
        gloss = time + rest + verbs + (["NOT"] if negated else []) + q
        intent = "question" if q or text.strip().endswith("?") else "statement"
        conf = 0.6
    ents = [Entity(text=w, type=t) for w, t in ENT.items() if w in clean.split()]
    return LLMResult(intent=intent, entities=ents, gloss=gloss or [clean.upper()], confidence=conf)

def parse_llm_json(raw: str) -> LLMResult:
    """Graceful recovery: strip fences / surrounding prose, then validate."""
    raw = re.sub(r"```(?:json)?", "", raw)
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise LLMError("no JSON in model output")
    try:
        data = json.loads(m.group(0))
        data["gloss"] = [str(g).upper().replace(" ", "_") for g in data.get("gloss", [])]
        return LLMResult(**data)
    except Exception as e:
        raise LLMError(f"invalid model JSON: {e}")

async def api_transform(text: str) -> LLMResult:
    if not settings.LLM_API_KEY:
        raise LLMError("LLM_API_KEY not set")
    body = {"model": settings.LLM_MODEL, "max_tokens": 500,
            "system": SYSTEM_PROMPT.format(target=settings.TARGET_SIGN_LANGUAGE),
            "messages": [{"role": "user", "content": text}]}
    headers = {"x-api-key": settings.LLM_API_KEY, "anthropic-version": "2023-06-01"}
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post("https://api.anthropic.com/v1/messages", json=body, headers=headers)
            r.raise_for_status()
        return parse_llm_json(r.json()["content"][0]["text"])
    except LLMError:
        raise
    except Exception as e:
        log.exception("LLM call failed")
        raise LLMError(str(e))

async def understand(text: str) -> tuple[LLMResult, str, str | None]:
    """Returns (result, engine, notice)."""
    if settings.LLM_PROVIDER == "api":
        try:
            return await api_transform(text), "api", None
        except LLMError as e:
            log.error("Falling back to mock: %s", e)
            return (mock_transform(text), "mock-fallback",
                    "AI translation is temporarily unavailable. Switching to fallback mode.")
    return mock_transform(text), "mock", None
