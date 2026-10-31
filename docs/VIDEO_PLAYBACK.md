# Signer-video playback and combined exports

Task 8 adds media-driven sequential playback alongside the avatar. Video
availability is separate from linguistic review: every unreviewed sequence keeps
the **demo / not verified ISL** label. Synthetic color cards used for tests are
not signer footage or sign definitions.

## Browser playback

The **Real signer videos / Avatar** toggle defaults to video only when the
complete, nonempty sequence has a `video_url` for every item. Streaming waits
until the sequence is complete before making this automatic choice. With partial
availability, Avatar is the default; users may explicitly choose videos if any
item has one. Missing items then appear as timed text cards, and the UI lists
their glosses. With no videos, the video option is disabled.

Video mode uses `HTMLMediaElement.ended` to advance; backend estimated sign
durations cannot truncate a recording. `loadedmetadata`/`timeupdate` provide
actual duration/progress. After each video it holds the last frame for the item's
`pause_after`, then loads the next. Repeated identical URLs restart from zero.
Shared controls support pause/resume/restart and 0.5x/1x/1.5x speed; speed affects
both videos and gaps. Buffering waits on media events. Playback failures display
an error with retry/Avatar options. Switching modes resets playback and pauses
the other controller. Missing-card timing uses the current sequence duration.

Videos are muted, and their playback is controlled by the sequence controls.
Before metadata arrives, timeline totals may use backend estimates; each loaded
clip updates its duration. Backend timing and avatar transitions are described
in [TIMING.md](TIMING.md).

## Combined export

**Generate combined video** is explicit and independent of translation. It does
not replace the normal player or require FFmpeg just to watch individual clips.
The API request remains `POST /api/generate-video` with `{sequence: [gloss, ...]}`.
The response retains `video_url` and adds `missing_glosses` and `notice`.

Available local videos are retained in order, including repeats. Missing files,
unknown glosses, explicit `FS:` tokens, and references escaping the sign folder
are skipped and listed. The UI displays that omission notice with the export.
No available clips still returns 422. A compiled video with omissions is not a
complete translation; the original sequence remains available.

Every input is first normalized to 640×480 letterboxed frames, square pixels,
25 fps, H.264/yuv420p, consistent timestamps/timebase, and no audio. An inter-sign
hold uses `INTER_SIGN_PAUSE` (default 0.2 seconds, five normalized frames) between retained clips.
Only internal numbered paths enter the concat file, so spaces/apostrophes in
source paths cannot corrupt its syntax. Normalized clips are concatenated into
an MP4. Working files and partial failed outputs are cleaned up. Each FFmpeg
process has a 120-second timeout. The compatibility `generate_video()` Python
wrapper still returns a URL; new callers should retain the structured notices.

Production export requires the configured `FFMPEG_BINARY` (normally on `PATH`, already included in the Docker
backend). Browser playback does not. An optional local integration-test binary
can be installed with `backend/requirements-video-test.txt`; that package is not
automatically added to production `PATH`.

## Checks performed

Backend tests cover collection order/repeats, missing references, safe concat
lists, normalization options, error cleanup, and API compatibility. The optional
real-FFmpeg test encodes two synthetic color videos with different dimensions
and frame rates, then decodes the generated MP4 to verify size, frame rate,
both source segments, and the inter-sign hold. It skips explicitly when the
optional binary is not installed.

Frontend tests use a fake media element and clock to cover media-ended chaining,
pauses, speed, missing cards, repeats, errors, reset, and appended items. A local
browser smoke check with synthetic 3-second/4-second clips confirmed video
defaulting, completion using actual durations, partial-availability Avatar
defaulting, and explicit missing-video notices. No licensed signer recordings
were supplied, so these checks establish player mechanics, not ISL fidelity.
