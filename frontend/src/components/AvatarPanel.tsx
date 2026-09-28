import { AnimatePresence, motion } from "framer-motion";
import type { SignItem } from "../types/translation";

/** Demo Sign Renderer. Swap for a Three.js / keypoint avatar later; props stay the same. */
export default function AvatarPanel({ item, videoUrl }: { item: SignItem | null; videoUrl: string | null }) {
  if (videoUrl) return <video src={videoUrl} controls className="aspect-video w-full rounded-card bg-black" aria-label="Generated sign video" />;
  return (
    <div className="relative grid aspect-video place-items-center overflow-hidden rounded-card bg-gradient-to-br from-indigo-50 via-white to-sky-50 ring-1 ring-black/5"
      role="img" aria-label={item ? `Current sign ${item.gloss}` : "Sign output"}>
      <div className="pointer-events-none absolute -top-16 left-1/4 h-56 w-56 rounded-full bg-accent/10 blur-3xl" />
      <div className="relative text-center">
        <AnimatePresence mode="wait">
          <motion.p key={item?.gloss ?? "idle"} initial={{ opacity: 0, scale: .97 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} transition={{ duration: .18 }}
            className={`text-5xl font-extrabold tracking-tight sm:text-6xl ${item && !item.available ? "text-warn" : "text-ink"}`}>
            {item ? item.gloss.replace("_", " ") : "Ready"}
          </motion.p>
        </AnimatePresence>
        {item && !item.available && <p className="mt-2 text-sm font-medium text-warn">Sign unavailable</p>}
      </div>
      <p className="absolute bottom-3 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full bg-white/80 px-3 py-1 text-xs font-medium text-muted ring-1 ring-black/5">
        Demo Sign Renderer · not an actual ISL sign
      </p>
    </div>
  );
}
