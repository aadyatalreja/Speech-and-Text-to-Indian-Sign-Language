import type { SignItem } from "../types/translation";

/** Rule provenance is independent of asset review and rendering quality. */
export default function NmmStatus({ item }: { item: SignItem | null | undefined }) {
  if (!item) return null;
  return <div role="status" aria-live="polite" aria-label="Current sign expression" className="space-y-1 text-xs text-muted">
    <p>NMM rules: {item.nmm_rules?.length ? item.nmm_rules.join(", ") : "none active"}</p>
  </div>;
}
