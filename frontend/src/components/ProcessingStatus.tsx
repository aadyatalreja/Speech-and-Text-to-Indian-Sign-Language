import type { Stage } from "../types/translation";
const LABEL: Record<Stage, string> = {
  idle: "", understanding: "Understanding sentence…", representing: "Generating sign representation…",
  preparing: "Preparing signs…", ready: "Ready", error: "",
};
export default function ProcessingStatus({ stage }: { stage: Stage }) {
  return <p role="status" aria-live="polite" className="min-h-7 font-bold">{LABEL[stage]}</p>;
}
