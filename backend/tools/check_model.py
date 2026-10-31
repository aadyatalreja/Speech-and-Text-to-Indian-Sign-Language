"""Optional authenticated read-only check of the configured Anthropic model ID."""
import asyncio
from pathlib import Path
import sys
from urllib.parse import quote

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from config import settings


async def check_model(client=None):
    if not settings.LLM_API_KEY:
        raise ValueError("LLM_API_KEY is required for the optional model availability check")
    async def query(connection):
        response = await connection.get("https://api.anthropic.com/v1/models/" + quote(settings.LLM_MODEL, safe=""),
            headers={"x-api-key": settings.LLM_API_KEY, "anthropic-version": "2023-06-01"})
        response.raise_for_status()
        data = response.json()
        if not isinstance(data.get("id"), str): raise ValueError("Model response has no id")
        return {"configured_id": settings.LLM_MODEL, "resolved_id": data["id"]}
    if client is not None: return await query(client)
    async with httpx.AsyncClient(timeout=15) as connection: return await query(connection)


def main():
    if not settings.LLM_API_KEY:
        print("LLM_API_KEY is required for the optional model availability check.", file=sys.stderr)
        return 1
    try:
        result = asyncio.run(check_model())
        print(f"Configured model available: {result['configured_id']} -> {result['resolved_id']}")
        return 0
    except Exception as exc:
        # Do not print request headers/response bodies containing account details.
        print(f"Model availability check failed ({type(exc).__name__}); check configuration and account access.", file=sys.stderr)
        return 1


if __name__ == "__main__": raise SystemExit(main())
