/** Signer looks. Arav/Dev share the male body, Anya/Devi the female body; the skeleton and every pose are identical.
 * Kept free of three.js so the page can render the picker without loading the 3D bundle. */
export type CharacterId = "arav" | "anya" | "dev" | "devi";

export const CHARACTERS: { id: CharacterId; name: string }[] = [
  { id: "arav", name: "Arav" },
  { id: "anya", name: "Anya" },
  { id: "dev", name: "Dev" },
  { id: "devi", name: "Devi" },
];

export const isCharacterId = (v: unknown): v is CharacterId => CHARACTERS.some(c => c.id === v);
