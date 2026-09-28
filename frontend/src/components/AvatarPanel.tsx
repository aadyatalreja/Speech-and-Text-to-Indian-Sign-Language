import { AnimatePresence, motion } from "framer-motion";
import type { SignItem } from "../types/translation";

/** Demo Sign Renderer. Replace this component with a Three.js/GLTF avatar driven by keypoints. */
export default function AvatarPanel({ item, playing, videoUrl }: { item: SignItem | null; playing: boolean; videoUrl: string | null }) {
  if (videoUrl) return <video src={videoUrl} controls className="aspect-video w-full rounded-xl border-2 border-ink bg-black" aria-label="Generated sign video" />;
  return (
    <div className="flex aspect-video flex-col items-center justify-center rounded-xl border-2 border-ink bg-ink p-4 text-paper" role="img" aria-label={item ? `Current sign ${item.gloss}` : "Sign output"}>
      <AnimatePresence mode="wait">
        <motion.p key={item?.gloss ?? "idle"} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}
          className={`text-5xl font-bold ${item && !item.available ? "text-saffron" : ""}`}>
          {item ? item.gloss.replace("_", " ") : "Press Play"}
        </motion.p>
      </AnimatePresence>
      {item && !item.available && <p className="mt-2 text-saffron">Sign unavailable</p>}
      {item?.available && item.asset_type === "demo" && <p className="mt-2 text-sm opacity-80">{playing ? "Showing" : "Paused on"} placeholder label, no real sign recorded yet</p>}
      <p className="mt-6 rounded bg-saffron px-2 py-1 text-sm font-bold text-ink">Demo Sign Renderer — not an actual ISL sign</p>
    </div>
  );
}
