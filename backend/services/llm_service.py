import json, logging, re
import httpx
from config import settings
from models.translation import LLMResult, Entity
from services.english_service import english_words, resolve_word, number_tokens
from services.sign_repository import SignRepository, get_repository
from services.vocabulary_service import select_vocabulary, validate_vocabulary
from services.grammar_service import active_rules, apply_grammar, drop_rule, use, verified_examples, grammar_notice
from models.grammar import GrammarUse

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
Configured grammar rules (JSON, including per-rule review status): {grammar}
Verified English-to-gloss examples (JSON): {examples}
Follow only the configured operations and verified examples. Draft rules are
engine-demo behavior, not validated ISL. If no verified examples are supplied,
do not fabricate or imply any. Do not infer classifiers, role shift, or signing
space coordinates from these limited rules. Pronoun references are labels only.
Allowed repository glosses (JSON): {vocabulary}
Use ONLY these exact glosses or explicit FS:<WORD> tokens. For names, unknown
words, numbers without an allowed entry, and anything outside this list, use
FS:<WORD> (uppercase letters/digits, underscores for multiword text). Never invent
glosses. Repository membership does not mean a sign or its grammar is verified.
Rules: preserve meaning; do not invent signs or sign IDs; return only valid JSON
like {{"intent":"statement|question|request|greeting","entities":[{{"text":"","type":""}}],"gloss":[{{"gloss":"HELLO","nmm":{{}},"fs":false}}],"sentence":{{"intent":"statement","question_type":null,"negated":false,"topic":null}},"confidence":0.0}}.
Leave nmm empty: numeric facial/head mappings come only from reviewed configuration.
This gloss is a computational intermediate representation, not an authoritative linguistic translation."""

class LLMError(Exception): ...

def mock_transform(text: str, repo: SignRepository | None = None) -> LLMResult:
    """English lookup followed by explicitly configured, review-labeled rules."""
    repo = repo or get_repository()
    rules = active_rules()
    words = english_words(text)
    tokens: list[tuple[str, str | None]] = []
    entities, used = [], []
    i = 0
    while i < len(words):
        word = words[i]
        sign, consumed = None, 1
        for end in range(len(words), i, -1):
            sign = repo.get_by_text(" ".join(words[i:end]))
            if sign:
                consumed = end - i
                break
        if not sign:
            sign = resolve_word(word.casefold() if i == 0 or word.isupper() else word, repo)
        if sign:
            tokens.append((sign.gloss, sign.category))
            if sign.category in {"location", "object"}:
                entities.append(Entity(text=" ".join(words[i:i + consumed]), type=sign.category.upper()))
        elif word.isdigit():
            tokens.extend((token, None) for token in number_tokens(word, repo))
        elif (rule := drop_rule(word, rules)) is not None:
            used.append(use(rule))
        else:
            tokens.append((f"FS:{word.upper()}", None))
        i += consumed
    intent = "question" if text.rstrip().endswith("?") or any(category == "question" for _, category in tokens) else "statement"
    gloss = [g for g, _ in tokens] or [f"FS:{w.upper()}" for w in words] or [f"FS:{text.strip().upper()}"]
    result = LLMResult(intent=intent, entities=entities, gloss=gloss, confidence=0.6, grammar_rules=used)
    return apply_grammar(result, text, repo, rules)

def parse_llm_json(raw: str) -> LLMResult:
    """Graceful recovery: strip fences / surrounding prose, then validate."""
    raw = re.sub(r"```(?:json)?", "", raw)
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise LLMError("no JSON in model output")
    try:
        data = json.loads(m.group(0))
        if not isinstance(data.get("gloss"), list):
            raise ValueError("gloss must be a list")
        normalized = []
        for item in data["gloss"]:
            token = {"gloss": item} if isinstance(item, str) else item
            if not isinstance(token, dict) or not isinstance(token.get("gloss"), str):
                raise ValueError("gloss tokens require a gloss string")
            normalized.append({**token, "gloss": re.sub(r"\s+", "_", token["gloss"].strip()).upper()})
        data["gloss"] = normalized
        return LLMResult(**data)
    except Exception as e:
        raise LLMError(f"invalid model JSON: {e}")

async def api_transform(text: str, repo: SignRepository | None = None) -> LLMResult:
    if not settings.LLM_API_KEY:
        raise LLMError("LLM_API_KEY not set")
    headers = {"x-api-key": settings.LLM_API_KEY, "anthropic-version": "2023-06-01"}
    try:
        repo = repo or get_repository()
        allowed = select_vocabulary(text, repo)
        rules = [rule for rule in active_rules() if rule.operation != "phrase" or
                 all(gloss in allowed for gloss in rule.gloss)]
        examples = verified_examples(allowed)
        body = {"model": settings.LLM_MODEL, "max_tokens": settings.LLM_MAX_TOKENS,
                "system": SYSTEM_PROMPT.format(target=settings.TARGET_SIGN_LANGUAGE,
                                               vocabulary=json.dumps(allowed),
                                               grammar=json.dumps([rule.model_dump() for rule in rules]),
                                               examples=json.dumps([example.model_dump() for example in examples])),
                "messages": [{"role": "user", "content": text}]}
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post("https://api.anthropic.com/v1/messages", json=body, headers=headers)
            r.raise_for_status()
        result = validate_vocabulary(parse_llm_json(r.json()["content"][0]["text"]), repo, allowed)
        # The model has seen every included rule; exact rule application cannot
        # be inferred from its output. Keep every draft influence disclosed and
        # never trust a model-supplied list of reviewed grammar claims.
        return result.model_copy(update={"grammar_rules": [use(rule) for rule in rules] + [GrammarUse(
            id="llm_ordering_not_signer_reviewed", source="Model-generated ordering; no signer review",
            review_status="unverified")]})
    except LLMError:
        raise
    except Exception as e:
        log.exception("LLM call failed")
        raise LLMError(str(e))

async def understand(text: str) -> tuple[LLMResult, str, str | None]:
    """Returns (result, engine, notice)."""
    if settings.LLM_PROVIDER == "api":
        try:
            result = await api_transform(text)
            return result, "api", grammar_notice(result.grammar_rules)
        except LLMError as e:
            log.error("Falling back to mock: %s", e)
            result = mock_transform(text)
            notice = "AI translation is temporarily unavailable. Switching to fallback mode."
            if draft := grammar_notice(result.grammar_rules):
                notice += " " + draft
            return result, "mock-fallback", notice
    result = mock_transform(text)
    return result, "mock", grammar_notice(result.grammar_rules)
