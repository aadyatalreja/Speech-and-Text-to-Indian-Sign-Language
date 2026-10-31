import { AnimatePresence, motion } from "framer-motion";
import { lazy, Suspense, useEffect, useState } from "react";
import type { SignItem } from "../types/translation";
import { avatarLabel, prefetchClips, videoLabel } from "../avatar/library";
import type { CompiledClip } from "../avatar/pose";

// three.js is only downloaded when a translation is shown
const AvatarCanvas = lazy(() => import("../avatar/AvatarCanvas"));

interface Props {
  item: SignItem | null;
  videoUrl: string | null;
  /** all items in the sequence, so remote clips can be prefetched before playback */
  items?: SignItem[];
  progress?: number;
  playing?: boolean;
}

/** 3D signer. Falls back to the text stage if WebGL is unavailable. Video output still wins when present. */
export default function AvatarPanel({ item, videoUrl, items = [], progress = 0, playing = false }: Props) {
  const [clip, setClip] = useState<CompiledClip | null>(null);
  const [noGL, setNoGL] = useState(false);

  useEffect(() => { if (items.length) void prefetchClips(items); }, [items]);

  if (videoUrl) return <div>
    <video src={videoUrl} controls className="aspect-video w-full rounded-card bg-black" aria-label="Generated sign video" />
    <p className="mt-2 text-center text-xs text-muted">{videoLabel(items)}</p>
  </div>;

  const label = item ? item.gloss.replace("_", " ") : "Ready";
  return (
    <div className="relative grid aspect-video place-items-center overflow-hidden rounded-card avatar-stage ring-1 ring-line/10"
      role="img" aria-label={item ? `Current sign ${item.gloss}` : "Sign output"}>
      <div className="pointer-events-none absolute -top-16 left-1/4 h-56 w-56 rounded-full bg-accent/20 blur-3xl" />

      {noGL ? (
        <AnimatePresence mode="wait">
          <motion.p key={label} initial={{ opacity: 0, scale: .97 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} transition={{ duration: .18 }}
            className="stage-text relative text-5xl font-extrabold tracking-tight text-ink sm:text-6xl">{label}</motion.p>
        </AnimatePresence>
      ) : (
        <Suspense fallback={<p className="relative text-sm text-muted">Loading avatar…</p>}>
          <AvatarCanvas item={item} progress={progress} playing={playing} onClip={setClip} onUnsupported={() => setNoGL(true)} />
        </Suspense>
      )}

      {!noGL && item && (
        <p className="pointer-events-none absolute left-3 top-3 rounded-full bg-surface/70 px-3 py-1 text-sm font-bold tracking-wide text-ink ring-1 ring-line/10 backdrop-blur">{label}</p>
      )}
      {!!item?.nmm_rules?.length && <p className="absolute right-3 top-12 rounded-full bg-surface/80 px-3 py-1 text-xs text-muted">
        {item.nmm_verified ? "NMM · reviewed rule" : "NMM · demo / not verified ISL"}
      </p>}
      {item && !item.available && !noGL && clip?.clip.kind !== "fingerspell" && (
        <p className="absolute right-3 top-3 rounded-full bg-warn-soft px-3 py-1 text-xs font-semibold text-warn">Sign unavailable</p>
      )}
      <p className="absolute bottom-3 left-1/2 w-max max-w-[95%] -translate-x-1/2 rounded-full bg-surface/70 px-3 py-1 text-center text-xs font-medium text-muted ring-1 ring-line/10 backdrop-blur">
        {noGL ? "Demo Sign Renderer · not an actual ISL sign" : avatarLabel(item ? clip : null)}
      </p>
    </div>
  );
}
