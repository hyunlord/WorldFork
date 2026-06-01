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
  // 50+ stat/essence field는 인덱스 시그니처로 수용 (state_v2 Character 직렬화)
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
  encounters?: Record<string, unknown>[];  // ★ 전투 enemy state (session encounters)
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

// ─── session-based state (★ harness 재설계 — v2_state_router global default 폐기) ───

export interface SessionStateResponse {
  session_id: string;
  current_hp: number;
  max_hp: number;
  inventory: string[];
  location: string;
  turn_count: number;
  floor_number: number;
  hours_in_dungeon: number;
  race: string;
  scenario_mode: string;
  absorbed_essences: Record<string, unknown>[];
  [key: string]: unknown;
}

// ★ 게임 화면 원작 명칭 (코드/문서 식별자만 투르윈/라스카니아 변환)
const _SCENARIO_NAME: Record<string, string> = { bjorn: "비요른" };
const _RACE_NAME: Record<string, string> = {
  barbarian: "바바리안",
  human: "인간 탐험가",
  dwarf: "드워프 탐험가",
  beastkin: "수인 탐험가",
  fairy: "요정 탐험가",
};

function playerNameFor(scenario: string, race: string): string {
  return _SCENARIO_NAME[scenario] ?? _RACE_NAME[race] ?? "탐험가";
}

// ★ 게임 화면 원작 명칭 역변환 — 코드/데이터는 IP 안전(라스카니아), 게임 출력만 원작(라프도니아)
const _UNMASK_IP: Record<string, string> = {
  라스카니아: "라프도니아",
  투르윈: "비요른",
};

export function unmaskIp(text: string): string {
  let result = text;
  for (const [masked, original] of Object.entries(_UNMASK_IP)) {
    result = result.split(masked).join(original);
  }
  return result;
}

export async function fetchSessionState(
  sessionId: string
): Promise<SessionStateResponse> {
  return fetchJSON<SessionStateResponse>(
    `${API_URL}/api/v2/session/${sessionId}/state`
  );
}

/**
 * SessionStateResponse(단일 플레이어 세션) → StateResponse(GameStateV2) 어댑터.
 * ★ harness 재설계: v2_state_router global default(투르윈+실렌+던전) 폐기.
 *   시작 파티원 0(자신만), 게임 화면 원작 명칭, session HP/위치 반영.
 */
export function sessionToStateResponse(s: SessionStateResponse): StateResponse {
  const name = playerNameFor(s.scenario_mode, s.race);
  return {
    state: {
      characters: {
        [name]: {
          name,
          race: s.race,
          hp: s.current_hp,
          hp_max: s.max_hp,
          is_player: true,
          inventory: { items: s.inventory.map((n) => ({ name: n })) },
          absorbed_essences: s.absorbed_essences,
          // ★ 장착 장비 (★ equipRows 무기 표시 — manual play "무기 없음" 해소)
          equipment: s.equipment,
          // ★ 진행 시스템 — statusData 키 정합 (영혼력/LV/정수 0 고정 해소)
          soul_power: s.soul_power,
          level: s.player_level,
          essences: s.absorbed_essences, // statusData essences 키 ↔ absorbed_essences
          max_essences: s.max_essences,
          xp: s.player_xp,
        } as unknown as CharacterV2,
      },
      world: {
        active_rifts: [],
        party_members: [name],
        hours_in_dungeon: s.hours_in_dungeon ?? 0,
        is_dark_zone: false,
      },
      location: {
        realm: unmaskIp(s.location),  // ★ 게임 화면 원작 명칭 (라프도니아)
        floor: s.floor_number ?? null,
        sub_area: null,
        // ★ rift_id → 던전 배경 이미지 매핑 (ui_rift_{id})
        rift_id: typeof s.rift_id === "string" ? s.rift_id : null,
        visibility_meters: 0,
        has_light: false,
      },
      // ★ 전투 enemy state — 5종 mechanic 결과(반사/조건부 회복 enemy HP) 시각화
      encounters: Array.isArray(s.encounters)
        ? (s.encounters as Record<string, unknown>[])
        : [],
    },
    turn: s.turn_count ?? 0,
  };
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
