"""Expire completed exports without traversing directories or symlinks."""

import asyncio
import logging
import time

log = logging.getLogger("signai.cleanup")


def cleanup_generated(root, ttl_minutes, now=None):
    cutoff = (time.time() if now is None else now) - ttl_minutes * 60
    for path in root.iterdir():
        if path.name == ".gitkeep" or path.is_symlink() or not path.is_file():
            continue
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
        except OSError:
            log.warning("Could not remove expired generated file %s", path.name)


async def cleanup_loop(root, ttl_minutes):
    while True:
        await asyncio.sleep(600)
        await asyncio.to_thread(cleanup_generated, root, ttl_minutes)
