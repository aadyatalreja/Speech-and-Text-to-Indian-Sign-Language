from abc import ABC, abstractmethod
from models.sign import SignSequenceItem
from services.sign_repository import SignRepository, get_repository

class SignGenerator(ABC):
    """Seam for a future neural generator (gloss -> pose sequence)."""
    @abstractmethod
    def generate(self, glosses: list[str]) -> list[SignSequenceItem]: ...

class SignSequenceService(SignGenerator):
    def __init__(self, repo: SignRepository | None = None):
        self.repo = repo or get_repository()

    def generate(self, glosses):
        return self.build(glosses)[0]

    def build(self, glosses: list[str], speed: float = 1.0):
        items, unknown = [], []
        for i, (g, sign) in enumerate(self.repo.get_sequence(glosses)):
            last = i == len(glosses) - 1
            if sign is None:
                unknown.append(g)
            items.append(SignSequenceItem(
                gloss=g, sign_id=sign.id if sign else None, available=sign is not None,
                duration=round((0.6 + 0.1 * len(g)) / speed, 2),
                pause_after=0.0 if last else round(0.2 / speed, 2),
                asset_type=sign.asset_type if sign else "none",
                video_url=f"/signs/{sign.video}" if sign and sign.video else None))
        return items, unknown
