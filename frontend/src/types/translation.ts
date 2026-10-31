export interface NonManualMarkers { brow?: number | null; head?: [number, number, number] | null; mouth?: number | null }
export interface GlossToken { gloss: string; nmm: NonManualMarkers; fs: boolean; nmm_rules: string[]; nmm_verified: boolean; reference?: string | null }
export interface GrammarUse { id: string; source: string; review_status: "unverified" | "in_review" | "verified"; reviewer: string | null }
export interface SentenceMetadata { intent: string; question_type: "wh" | "yes_no" | null; negated: boolean; topic: string | null }
export interface SignItem { gloss: string; sign_id: string | null; available: boolean; duration: number; pause_after: number; asset_type: string; video_url: string | null; clip_url?: string | null; nmm?: NonManualMarkers; nmm_rules?: string[]; nmm_verified?: boolean; source?: string | null; licence?: string | null; signer?: string | null; review_status?: "unverified" | "in_review" | "verified"; needs_manual_review?: boolean; sequence_index?: number; timing_source?: string; clip_duration?: number | null; video_duration?: number | null; transition_duration?: number }
export interface Entity { text: string; type: string }
export interface Translation {
  original_text: string; target_sign_language: string; intent: string; entities: Entity[];
  gloss: string[]; sequence: SignItem[]; unknown_signs: string[]; confidence: number; engine: string; notice: string | null;
  gloss_detail?: GlossToken[]; sentence?: SentenceMetadata;
  grammar_rules?: GrammarUse[];
}
export interface SignAnimationController { play(): void; pause(): void; resume(): void; restart(): void; setSpeed(s: number): void }
export type Stage = "idle" | "understanding" | "representing" | "preparing" | "ready" | "error";
