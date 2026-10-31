import json
from abc import ABC, abstractmethod
from config import settings
from models.sign import Sign

def normalize_text(text: str) -> str:
    """English lookup normalization; makes no linguistic ISL claims."""
    return " ".join(text.replace("_", " ").casefold().split())

class SignRepository(ABC):
    @abstractmethod
    def get_sign(self, gloss: str) -> Sign | None: ...
    @abstractmethod
    def search(self, query: str) -> list[Sign]: ...
    def get_by_text(self, word: str) -> Sign | None:
        return self.get_sign(word)
    def list_glosses(self) -> list[str]:
        return [s.gloss for s in self.search("")]
    def list_by_category(self, category: str) -> list[Sign]:
        return [s for s in self.search("") if s.category and
                normalize_text(s.category) == normalize_text(category)]
    def get_sequence(self, glosses: list[str]) -> list[tuple[str, Sign | None]]:
        return [(g, self.get_sign(g)) for g in glosses]

class JsonSignRepository(SignRepository):
    def __init__(self, path=None):
        path = path or settings.SIGN_DATA_PATH / "signs.json"
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        self._signs = {k.upper(): Sign(**v) for k, v in raw.items()}
        self._aliases: dict[str, Sign] = {}
        ids: set[str] = set()
        for key, sign in self._signs.items():
            sign_id = normalize_text(sign.id)
            if sign_id in ids:
                raise ValueError(f"Duplicate sign id: {sign.id}")
            ids.add(sign_id)
            for name in [key, sign.gloss, *sign.aliases, *([sign.lemma] if sign.lemma else [])]:
                name = normalize_text(name)
                previous = self._aliases.get(name)
                if previous is not None and previous is not sign:
                    raise ValueError(f"Ambiguous sign alias: {name}")
                self._aliases[name] = sign

    def get_sign(self, gloss):
        return self._signs.get(gloss.upper())

    def get_by_text(self, word):
        return self._aliases.get(normalize_text(word))

    def search(self, query):
        q = normalize_text(query)
        matches = {s.id for name, s in self._aliases.items() if q in name}
        return [s for s in self._signs.values() if s.id in matches]

_repo: SignRepository | None = None
def get_repository() -> SignRepository:
    global _repo
    if _repo is None:
        _repo = JsonSignRepository()
    return _repo
