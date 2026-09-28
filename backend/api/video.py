from fastapi import APIRouter, HTTPException
from models.translation import VideoRequest
from services.video_service import generate_video, VideoError

router = APIRouter()

@router.post("/generate-video")
def generate(req: VideoRequest):
    try:
        return {"video_url": generate_video(req.sequence)}
    except VideoError as e:
        raise HTTPException(422, f"{e} The sign sequence is still available.")
