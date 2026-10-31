import shutil, subprocess, uuid, logging, tempfile
from pathlib import Path
from pydantic import BaseModel
from config import settings
from services.sign_repository import get_repository

log = logging.getLogger("signai.video")

class VideoError(Exception): ...

class VideoResult(BaseModel):
    video_url: str
    missing_glosses: list[str]
    notice: str | None = None


def collect_clips(glosses):
    repo = get_repository()
    root = settings.SIGN_DATA_PATH.resolve()
    clips, missing = [], []
    for g in glosses:
        s = None if g.upper().startswith("FS:") else repo.get_sign(g)
        if s and s.review_decision == "rejected": s = None
        path = (root / s.video).resolve() if s and s.video else None
        if path is not None and path.is_relative_to(root) and path.is_file():
            clips.append(path)
        else:
            missing.append(g)
    return clips, missing


def concat_list(count):
    """Only internal filenames enter concat syntax; input paths stay argv."""
    return "".join(f"file '{index:04d}.mp4'\n" for index in range(count))


def normalize_command(source, target, gap, executable="ffmpeg"):
    filters = ("setpts=PTS-STARTPTS,fps=25,scale=640:480:force_original_aspect_ratio=decrease,"
               "pad=640:480:(ow-iw)/2:(oh-ih)/2,setsar=1")
    if gap:
        # Frame counts avoid tpad duration interpretation using an inherited
        # source frame rate after FPS conversion (notably for short clips).
        filters += f",tpad=stop_mode=clone:stop={round(gap * 25)}"
    return [executable, "-nostdin", "-y", "-i", str(source), "-map", "0:v:0", "-an",
            "-vf", filters, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "25",
            "-video_track_timescale", "12800", str(target)]


def generate_video_result(glosses: list[str]) -> VideoResult:
    clips, missing = collect_clips(glosses)
    if not clips:
        raise VideoError("No video assets available for this sequence.")
    executable = shutil.which(settings.FFMPEG_BINARY)
    if not executable:
        raise VideoError("FFmpeg is not installed.")
    settings.GENERATED_PATH.mkdir(parents=True, exist_ok=True)
    name = f"translation_{uuid.uuid4().hex}.mp4"
    out = settings.GENERATED_PATH / name
    try:
        with tempfile.TemporaryDirectory(prefix=".video-", dir=settings.GENERATED_PATH) as directory:
            work = Path(directory)
            for index, source in enumerate(clips):
                subprocess.run(normalize_command(source, work / f"{index:04d}.mp4",
                    settings.INTER_SIGN_PAUSE if index < len(clips) - 1 else 0, executable), check=True, capture_output=True, timeout=120)
            playlist = work / "concat.txt"
            playlist.write_text(concat_list(len(clips)), encoding="utf-8")
            subprocess.run([executable, "-nostdin", "-y", "-f", "concat", "-safe", "1", "-i", str(playlist),
                "-an", "-c:v", "copy", "-movflags", "+faststart", str(out)], check=True, capture_output=True, timeout=120)
    except Exception as exc:
        out.unlink(missing_ok=True)
        log.exception("ffmpeg failed")
        raise VideoError("Video generation failed; check the source clips and FFmpeg installation.") from exc
    return VideoResult(video_url=f"/generated/{name}", missing_glosses=missing,
        notice="Missing signer videos skipped: " + ", ".join(missing) + "." if missing else None)


def generate_video(glosses: list[str]) -> str:
    """Compatibility wrapper; new callers should retain result notices."""
    return generate_video_result(glosses).video_url
