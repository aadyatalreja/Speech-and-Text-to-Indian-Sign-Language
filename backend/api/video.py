from threading import BoundedSemaphore
from fastapi import APIRouter, HTTPException, Request
from config import settings
from services.rate_limit import check_rate
from models.translation import VideoRequest
from services.video_service import generate_video_result, VideoError, VideoResult

router = APIRouter()
video_jobs = BoundedSemaphore(settings.MAX_VIDEO_JOBS)


@router.post("/generate-video", response_model=VideoResult)
def generate(req: VideoRequest, request: Request):
    check_rate(request, "video", settings.RATE_LIMIT_VIDEO_PER_MIN)
    if not video_jobs.acquire(blocking=False):
        raise HTTPException(
            429, "Video generation is busy. Please retry later.", headers={"Retry-After": "1"}
        )
    try:
        return generate_video_result(req.sequence)
    except VideoError as e:
        raise HTTPException(422, f"{e} The sign sequence is still available.")
    finally:
        video_jobs.release()
