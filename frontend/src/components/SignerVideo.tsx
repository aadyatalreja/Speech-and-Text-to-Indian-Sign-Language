import type { SignItem } from "../types/translation";
import { videoLabel } from "../avatar/library";

export default function SignerVideo({ item, items, mediaRef, gap }: {
  item: SignItem | null; items: SignItem[]; mediaRef: (element: HTMLVideoElement | null) => void; gap: boolean;
}) {
  return <div>
    <div className="relative grid aspect-video place-items-center overflow-hidden rounded-card bg-black">
      <video ref={mediaRef} muted playsInline preload="metadata" className={`h-full w-full object-contain ${item?.video_url ? "" : "hidden"}`} aria-label="Sequential signer video" />
      {!item && <p className="absolute text-sm text-white">Press Play to start signer videos.</p>}
      {item && !item.video_url && <p role="status" className="absolute px-4 text-center text-white">{item.gloss} · no signer video; text only</p>}
      {gap && <p className="absolute bottom-3 rounded-full bg-black/70 px-3 py-1 text-xs text-white">Inter-sign pause</p>}
    </div>
    <p className="mt-2 text-center text-xs text-muted">{videoLabel(items)}</p>
  </div>;
}
