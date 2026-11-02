"""Bounded parsed-file cache. Return copies so request code cannot mutate it."""

from copy import deepcopy
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=64)
def _parse(path, mtime_ns, size, parser):
    return parser(Path(path).read_text(encoding="utf-8"))


def cached_file(path, parser):
    path = Path(path).resolve()
    stat = path.stat()
    return deepcopy(_parse(str(path), stat.st_mtime_ns, stat.st_size, parser))
