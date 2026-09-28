from pydantic import BaseModel

class Sign(BaseModel):
    id: str
    gloss: str
    asset_type: str = "demo"  # demo | dataset
    video: str | None = None
    keypoints: str | None = None

class SignSequenceItem(BaseModel):
    gloss: str
    sign_id: str | None
    available: bool
    duration: float
    pause_after: float = 0.2
    asset_type: str = "demo"
    video_url: str | None = None
