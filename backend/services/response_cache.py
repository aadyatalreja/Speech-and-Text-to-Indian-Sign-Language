"""Process-local LRU/TTL cache of successful model results; copies isolate requests."""

from collections import OrderedDict
import time

from config import settings


class ResponseCache:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.items = OrderedDict()

    def clear(self):
        self.items.clear()

    def get(self, key):
        if settings.LLM_CACHE_SIZE == 0:
            self.clear()
            return None
        item = self.items.pop(key, None)
        if item is None:
            return None
        expires, value = item
        if self.clock() >= expires:
            return None
        self.items[key] = item
        return value.model_copy(deep=True)

    def put(self, key, value):
        if settings.LLM_CACHE_SIZE == 0:
            return
        self.items[key] = (
            self.clock() + settings.LLM_CACHE_TTL_SECONDS,
            value.model_copy(deep=True),
        )
        self.items.move_to_end(key)
        while len(self.items) > settings.LLM_CACHE_SIZE:
            self.items.popitem(last=False)
