# Experimental SignClip v2

V1 files and `AvatarRig.applyPose` remain supported. No existing clip or registry
entry is rewritten. `adaptClip` copies v1 into the v2 schema and preserves v1
hand defaults. compileClip, sampleClip, transitionPose and PoseFollower share the
resolved pose representation. Rotations use shortest-path quaternion slerp;
scalar tracks use linear interpolation with the existing smoothstep time easing.

## Channels and conventions

`version: 2` keeps the v1 metadata and keyframe `t`, R/L, head, brow and mouth.
A hand may supply only changed fields: position `p`, wrist orientation `wrist`
(or the v1 `q`/Euler `rot`), shape, spread, thumbOut and `fingers`. Omitted fields
hold the previous value; null returns the hand to rest. Fingers, when present,
are exactly 15 local quaternion rotations `[x,y,z,w]`: thumb, index, middle,
ring, pinky, each proximal to distal. The wrist is a separate quaternion.
Neutral segment axes point +Y; +X flexes toward the palm. Legacy spread and
thumb-base abduction remain separate controls. Without finger data the original
curl model applies; mixed transitions derive curl-equivalent joint rotations.

Optional per-keyframe `face` scalar channels:

- mouth_open, mouth_wide, mouth_round, brow_inner_up, brow_down_left,
  brow_down_right and eye_blink: 0..1;
- gaze_x, gaze_y: -1..1, positive toward viewer-right and up.

Optional `torso` channels: lean_x and lean_z in degrees (-30..30),
shoulder_raise_left/right in shoulder widths (0..0.3). Each scalar has its own
track so omitted channels hold. Unmentioned extension channels are neutral.
Legacy brow/mouth channels still animate the procedural face. Item NMM may add
`gaze: [x,y]` and `mouth_shape: {open,wide,round}` with the same bounds; validators
reject nonfinite/out-of-range values. Shipped question/negation NMM rules are enabled
demo rig values, unverified and requiring signer review. Numeric amplitudes,
sentence scope and the engine-generated headshake remain illustrative. Current
rule IDs and an unverified-expression badge are shown below the avatar; see the
README for reference leads, review TODOs and interpolation limitations.
Numeric channels and meshes do not establish meaningful ISL non-manual grammar.

## Converter and lab

```text
python backend/tools/mediapipe_to_clip.py local/landmarks.json local/clip-v2.json --gloss SAMPLE --id sample --format 2
```

Default `--format 1` is unchanged. Format 2 estimates separate signed joint
flexions from the Holistic hand chains and smooths sign-aligned unit quaternions
with the existing temporal window. Splay and thumb placement remain approximate.
Notes explicitly warn that monocular depth is noisy; this is not full motion
capture, reliable axial twist reconstruction, or signer-verified animation.

Open `/lab.html` in the frontend development server. Paste a v1/v2 clip or choose
SYNTHETIC_JOINTS, SYNTHETIC_FACE or SYNTHETIC_TORSO. Scrub, loop and choose a
previous v1/v2 clip to inspect transitions. The output shows sampled face, torso
and finger values. These fixtures are lab-only software examples, never entries
in signs.json or definitions of actual signs.

## Optional user-supplied glTF model

Set `VITE_AVATAR_MODEL_URL=/models/your-humanoid.glb` before starting/building the
frontend. Supply the file yourself (for that example, under frontend/public/models).
No model is bundled, downloaded by this task, or loaded when the variable is unset.
**You must hold the rights to use and serve any model, textures and linked assets
you supply.** The configured URL and its dependencies are fetched by the browser;
ensure they are reachable and allow the application's origin.

This experimental retargeter supports a named humanoid hierarchy, facing +Z with
+Y up. Required bones: Spine, Head, LeftArm/LeftUpperArm, RightArm/RightUpperArm,
LeftForeArm/LeftLowerArm, RightForeArm/RightLowerArm, LeftHand, RightHand.
Names ignore case/punctuation and an optional Mixamo prefix. Optional finger bones
use LeftHand/RightHand + Thumb/Index/Middle/Ring/Pinky + 1/2/3. Local finger axes
must follow the clip convention; model-specific retargeting may be needed.
Optional morph targets use the exact face-channel names. Unsupported morphs/bones
cannot reproduce those channels. Shoulder width normalizes model scale and origin;
procedural IK supplies arm targets. This is not a general VRM/humanoid retargeting
standard, and arbitrary glTF skeletons are not automatically compatible.

The procedural rig stays active during loading. A loading, skeleton-validation or
animation error falls back to it. Inspect all retargeted motion in the lab before
using your model; no linguistic quality is claimed for either rig.
