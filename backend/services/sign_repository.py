import json
from abc import ABC, abstractmethod
from config import settings
from models.sign import Sign

class SignRepository(ABC):
    @abstractmethod
    def get_sign(self, gloss: str) -> Sign | None: ...
    @abstractmethod
    def search(self, query: str) -> list[Sign]: ...
    def get_sequence(self, glosses: list[str]) -> list[tuple[str, Sign | None]]:
        return [(g, self.get_sign(g)) for g in glosses]

class JsonSignRepository(SignRepository):
    def __init__(self, path=None):
        path = path or settings.SIGN_DATA_PATH / "signs.json"
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        self._signs = {k.upper(): Sign(**v) for k, v in raw.items()}

    def get_sign(self, gloss):
        return self._signs.get(gloss.upper())

    def search(self, query):
        q = query.upper()
        return [s for k, s in self._signs.items() if q in k]

_repo: SignRepository | None = None
def get_repository() -> SignRepository:
    global _repo
    if _repo is None:
        _repo = JsonSignRepository()
    return _repo
