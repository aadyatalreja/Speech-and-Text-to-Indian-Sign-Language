from fastapi import APIRouter, HTTPException
from models.translation import VideoRequest
from services.video_service import generate_video_result, VideoError, VideoResult

router = APIRouter()

@router.post("/generate-video", response_model=VideoResult)
def generate(req: VideoRequest):
    try:
        return generate_video_result(req.sequence)
    except VideoError as e:
        raise HTTPException(422, f"{e} The sign sequence is still available.")
