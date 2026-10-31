import shutil, subprocess, uuid, logging
from config import settings
from services.sign_repository import get_repository

log = logging.getLogger("signai.video")

class VideoError(Exception): ...

def generate_video(glosses: list[str]) -> str:
    """Concatenate real sign clips with FFmpeg. Demo signs have no clips -> VideoError."""
    repo = get_repository()
    clips = []
    for g in glosses:
        s = repo.get_sign(g)
        if s and s.video and (settings.SIGN_DATA_PATH / s.video).exists():
            clips.append(settings.SIGN_DATA_PATH / s.video)
    if not clips:
        raise VideoError("No video assets available for this sequence.")
    if not shutil.which("ffmpeg"):
        raise VideoError("FFmpeg is not installed.")
    settings.GENERATED_PATH.mkdir(exist_ok=True)
    name = f"translation_{uuid.uuid4().hex[:8]}.mp4"
    out = settings.GENERATED_PATH / name
    lst = settings.GENERATED_PATH / f"{name}.txt"
    lst.write_text("".join(f"file '{c.resolve()}'\n" for c in clips))
    try:
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)],
                       check=True, capture_output=True, timeout=120)
    except Exception:
        log.exception("ffmpeg failed")
        raise VideoError("Video generation failed.")
    finally:
        lst.unlink(missing_ok=True)
    return f"/generated/{name}"
