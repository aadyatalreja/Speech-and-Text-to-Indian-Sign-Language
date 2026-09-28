export interface SignItem { gloss: string; sign_id: string | null; available: boolean; duration: number; pause_after: number; asset_type: string; video_url: string | null }
export interface Entity { text: string; type: string }
export interface Translation {
  original_text: string; target_sign_language: string; intent: string; entities: Entity[];
  gloss: string[]; sequence: SignItem[]; unknown_signs: string[]; confidence: number; engine: string; notice: string | null;
}
export interface SignAnimationController { play(): void; pause(): void; resume(): void; restart(): void; setSpeed(s: number): void }
export type Stage = "idle" | "understanding" | "representing" | "preparing" | "ready" | "error";
