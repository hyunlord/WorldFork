/**
 * Tier 2 state API client (★ Phase 7b).
 *
 * 본 모듈 본격:
 * - GET /api/v2/state — 현재 Tier 2 GameState V2
 * - GET /api/v2/state/recent_actions — 최근 N 행동
 * - POST /api/v2/state/reset — 본격 default 재초기화
 *
 * 본격 본격: NEXT_PUBLIC_API_URL (★ default localhost:8090, 기존 정합).
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8090";

// ─── types (★ backend Pydantic response 본격 정합) ───

export interface CharacterV2 {
  name: string;
  race: string;
  hp: number;
  hp_max: number;
  is_player: boolean;
  // ★ 본 commit 본격 본격 — 본격 50+ field 본격 본격 본격 본격 본격
  [key: string]: unknown;
}

export interface WorldStateV2 {
  active_rifts: string[];
  party_members: string[];
  hours_in_dungeon: number;
  is_dark_zone: boolean;
  [key: string]: unknown;
}

export interface LocationV2 {
  realm: string;
  floor: number | null;
  sub_area: string | null;
  rift_id: string | null;
  visibility_meters: number;
  has_light: boolean;
}

export interface GameStateV2 {
  characters: Record<string, CharacterV2>;
  world: WorldStateV2;
  location: LocationV2;
}

export interface StateResponse {
  state: GameStateV2;
  turn: number;
}

export interface RecentActionsResponse {
  actions: Record<string, unknown>[];
  count: number;
  total: number;
}

export interface ResetResponse {
  status: string;
  turn: number;
}

// ─── helpers ───

async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, { cache: "no-store", ...init });
  if (!res.ok) {
    let detail = "";
    try {
      const data = await res.json();
      detail = JSON.stringify(data);
    } catch {
      detail = await res.text();
    }
    throw new Error(`API ${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

// ─── endpoints ───

export async function fetchCurrentState(): Promise<StateResponse> {
  return fetchJSON<StateResponse>(`${API_URL}/api/v2/state`);
}

export async function fetchRecentActions(
  n: number = 10
): Promise<RecentActionsResponse> {
  return fetchJSON<RecentActionsResponse>(
    `${API_URL}/api/v2/state/recent_actions?n=${n}`
  );
}

export async function resetState(): Promise<ResetResponse> {
  return fetchJSON<ResetResponse>(`${API_URL}/api/v2/state/reset`, {
    method: "POST",
  });
}

// ─── Phase 7k: action endpoint ───

export interface ActionRequest {
  action_type: string;
  actor?: string;
  target?: string;
  rationale?: string;
}

export interface ActionResponse {
  success: boolean;
  message: string;
  side_effects: string[];
  state: GameStateV2;
  turn: number;
}

export async function postAction(
  req: ActionRequest
): Promise<ActionResponse> {
  return fetchJSON<ActionResponse>(`${API_URL}/api/v2/action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
}
