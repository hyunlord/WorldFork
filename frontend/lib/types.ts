/**
 * API 타입 (★ service/api/models.py 미러).
 *
 * Tier 2 D9 W3 — TypeScript + Pydantic 일치.
 */

export interface StartGameRequest {
  work_url?: string | null;
  work_name?: string | null;
}

export interface StartGameResponse {
  session_id: string;
  plan: {
    work_name?: string;
    world_setting?: string;
    opening_scene?: string;
  };
  initial_state: {
    turn: number;
    location?: string;
  };
  message: string;
}

export interface TurnRequest {
  session_id: string;
  user_action: string;
}

export interface TurnResponse {
  response: string;
  turn_n: number;
  mechanical_passed: boolean;
  truncated: boolean;
  total_score: number;
  verify_passed: boolean;
}

export interface GameStateResponse {
  session_id: string;
  turn: number;
  location: string;
  history: Array<{
    turn: number;
    user_action: string;
    gm_response: string;
  }>;
}

export type MessageType = "user" | "gm" | "system" | "error";

export interface Message {
  id: string;
  type: MessageType;
  content: string;
  timestamp: number;
}

export interface FunRating {
  score: number; // 1-5
  comment?: string | null;
}

export interface Finding {
  category: string;
  description: string;
  severity: "critical" | "major" | "minor";
}

export interface EndSessionRequest {
  session_id: string;
  fun_rating?: FunRating | null;
  findings?: Finding[];
  comment?: string | null;
}

export interface EndSessionResponse {
  session_id: string;
  saved_path: string;
  total_turns: number;
  summary: {
    fun_score?: number | null;
    findings_count: number;
    history_length: number;
  };
}
