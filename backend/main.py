import logging
import asyncio
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from api import assets, health, translation, video, feedback
from config import settings
from services.generated_cleanup import cleanup_generated, cleanup_loop
from services.llm_service import start_client, close_client

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app):
    start_client()
    task = None
    try:
        await asyncio.to_thread(
            cleanup_generated, settings.GENERATED_PATH, settings.GENERATED_TTL_MINUTES
        )
        task = asyncio.create_task(
            cleanup_loop(settings.GENERATED_PATH, settings.GENERATED_TTL_MINUTES)
        )
        yield
    finally:
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        await close_client()


app = FastAPI(title="SignAI", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"]
)
for r in (health.router, translation.router, video.router, feedback.router):
    app.include_router(r, prefix="/api")
settings.GENERATED_PATH.mkdir(parents=True, exist_ok=True)
settings.SIGN_DATA_PATH.mkdir(parents=True, exist_ok=True)
# sign videos and avatar clips; clips are loaded by the browser from /signs/<clip path>
app.include_router(assets.router)
app.mount("/generated", StaticFiles(directory=settings.GENERATED_PATH), name="generated")


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": "Please enter a sentence."})
