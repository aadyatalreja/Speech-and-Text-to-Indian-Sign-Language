import type { SignItem } from "../types/translation";

/** Rule provenance is independent of asset review and rendering quality. */
export default function NmmStatus({ item }: { item: SignItem | null | undefined }) {
  void item; // NMM rule text is intentionally not shown in the UI.
  return null;
}
