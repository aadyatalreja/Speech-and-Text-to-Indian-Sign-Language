"""Process-local token buckets; use the direct peer, never untrusted proxy headers."""

import math
import time
from threading import Lock

from fastapi import HTTPException


class RateLimiter:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.buckets = {}
        self.lock = Lock()

    def retry_after(self, client, group, capacity):
        with self.lock:
            now = self.clock()
            # Fully refilled buckets need no stored state. Bound idle-IP growth.
            self.buckets = {
                key: value for key, value in self.buckets.items() if now - value[1] < 60
            }
            key = (client, group)
            tokens, previous = self.buckets.get(key, (float(capacity), now))
            tokens = min(capacity, tokens + (now - previous) * capacity / 60)
            if tokens < 1:
                return max(1, math.ceil((1 - tokens) * 60 / capacity))
            self.buckets[key] = (tokens - 1, now)
            return 0


limiter = RateLimiter()


def check_rate(request, group, capacity):
    peer = request.client.host if request.client else "unknown"
    retry = limiter.retry_after(peer, group, capacity)
    if retry:
        raise HTTPException(
            429, "Rate limit exceeded. Please retry later.", headers={"Retry-After": str(retry)}
        )
