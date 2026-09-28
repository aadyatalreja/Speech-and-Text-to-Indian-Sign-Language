import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from api import health, translation, video
from config import settings

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="SignAI")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                   allow_methods=["*"], allow_headers=["*"])
for r in (health.router, translation.router, video.router):
    app.include_router(r, prefix="/api")
settings.GENERATED_PATH.mkdir(exist_ok=True)
app.mount("/generated", StaticFiles(directory=settings.GENERATED_PATH), name="generated")

@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": "Please enter a sentence."})
