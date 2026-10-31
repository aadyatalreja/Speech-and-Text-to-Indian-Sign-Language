from abc import ABC, abstractmethod
from models.sign import SignSequenceItem
from services.sign_repository import SignRepository, get_repository
from services.english_service import resolve_word
from models.markers import GlossToken
from config import settings
from services.timing_service import item_timing
import math

class SignGenerator(ABC):
    """Seam for a future neural generator (gloss -> pose sequence)."""
    @abstractmethod
    def generate(self, glosses: list[str]) -> list[SignSequenceItem]: ...

class SignSequenceService(SignGenerator):
    def __init__(self, repo: SignRepository | None = None):
        self.repo = repo or get_repository()

    def generate(self, glosses):
        return self.build(glosses)[0]

    def build(self, glosses: list[str] | list[GlossToken], speed: float = 1.0):
        if not math.isfinite(speed) or speed <= 0:
            raise ValueError("speed must be finite and positive")
        items, unknown = [], []
        for i, raw in enumerate(glosses):
            token = GlossToken(gloss=raw) if isinstance(raw, str) else raw
            g = token.gloss
            explicit_fs = g.upper().startswith("FS:")
            sign = None if explicit_fs else resolve_word(g.casefold(), self.repo)
            if sign and sign.review_decision == "rejected":
                sign = None
            if sign:
                g = sign.gloss
            last = i == len(glosses) - 1
            if sign is None:
                unknown.append(g[3:] if explicit_fs else g)
                if not explicit_fs:
                    g = f"FS:{g.upper()}"
            duration, timing_source, clip_duration, video_duration = item_timing(sign, g)
            items.append(SignSequenceItem(
                gloss=g, sign_id=sign.id if sign else None, available=sign is not None,
                duration=duration / speed,
                pause_after=0.0 if last else settings.INTER_SIGN_PAUSE / speed,
                asset_type=sign.asset_type if sign else "none",
                video_url=f"/signs/{sign.video}" if sign and sign.video else None,
                clip_url=f"/signs/{sign.clip}" if sign and sign.clip and sign.clip_review_decision != "rejected" else None,
                nmm=token.nmm, nmm_rules=token.nmm_rules, nmm_verified=token.nmm_verified,
                reference=token.reference, source=sign.source if sign else None,
                licence=sign.licence if sign else None, signer=sign.signer if sign else None,
                review_status=sign.review_status if sign else "unverified",
                needs_manual_review=sign.needs_manual_review if sign else True,
                sequence_index=i, timing_source=timing_source,
                clip_duration=clip_duration / speed if clip_duration else None,
                video_duration=video_duration / speed if video_duration else None,
                transition_duration=min(settings.AVATAR_TRANSITION_SECONDS, duration / 2) / speed))
        return items, unknown
