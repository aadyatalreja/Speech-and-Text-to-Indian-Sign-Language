# Timing and transitions

Sequence duration resolution is: existing clip v1 `duration`, registered clip
duration metadata, FFprobe video stream/container duration, registered video
duration metadata, then a disclosed fallback. Clip timing has precedence for
avatar items; separate `clip_duration` and `video_duration` fields retain both.
The browser video player always uses actual media completion rather than the
avatar duration. Imported original video metadata uses decoded frame count/fps;
FFprobe measurements take precedence when available.

Unknown spelling tokens use `0.6 + 0.1 * len(payload)` as a backend estimate;
loaded alphabet composition provides frontend timing. Known demo entries use
the fixed `DEMO_SIGN_DURATION` instead of a gloss-length formula. `timing_source`
identifies clip/video or spelling/demo estimate. Invalid/unavailable duration
data never produces NaN or negative playback. File-stat keyed caches invalidate
when asset files change. FFprobe failures fall back with a log notice; source
paths must remain inside the configured sign directory.

`INTER_SIGN_PAUSE` controls sequence gaps and combined-export holds; the final
item has no trailing pause. Export gap duration is quantized to 25 fps. Positive
service speed scales sign/pause/transition durations consistently; browser speed
changes preserve elapsed base time. The avatar timer does not carry a completed
sign's elapsed time into the next sign, and streamed items can resume playback
after catching up.

`AVATAR_TRANSITION_SECONDS` defaults to 0.18 and is capped at half a sign. A
smooth blend interpolates hands, orientations, fingers, head, brows and mouth
from the preceding clip's end pose into the current clip motion. It does not
insert an invented sign or claim linguistically correct coarticulation. NMM
overrides remain part of the compiled poses being blended. Zero disables the
blend. The existing PoseFollower adds frame-to-frame smoothing.

In `/lab.html`, select a **Previous clip for transition preview** and scrub near
zero. Transition zero starts exactly at the previous end, and the blend reaches
the next clip without a rest reset. The numerical preview uses the same blend
function as the canvas. All bundled clips remain demo/not verified ISL.
