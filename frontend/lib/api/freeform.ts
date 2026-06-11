/**
 * Phase D — POST /api/v2/freeform_action client.
 *
 * Backend endpoint (commit 5d04091):
 * - 9B intent classifier → score ≥ 0.8 시 intent path
 * - 27B free-form fallback (★ narrative + state_delta)
 *
 * 본 commit 본 wire-up — InputBar.onSubmit 의 호출 destination.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8090";

export type FreeformResolvedPath = "intent" | "fallback";

export interface FreeformStateDelta {
  hp_change: number;
  inventory_add: string[];
  inventory_remove: string[];
  location: string | null;
  time_advance: number;
  affinity_changes: Record<string, number>;
}

export interface FreeformSessionSummary {
  current_hp: number;
  max_hp: number;
  inventory: string[];
  location: string;
  turn_count: number;
}

export interface FreeformActionResponse {
  resolved_path: FreeformResolvedPath;
  matched_action: string | null;
  confidence: number | null;
  narrative: string;
  state_delta: FreeformStateDelta;
  fallback_reason: string | null;
  session_id: string | null;
  session_state: FreeformSessionSummary | null;
  suggested_actions?: string[];
  // ★ 서빙 3단계 — GM 라우팅 관측: "9b"(단순) / "27b"(pivotal) / null
  gm_model?: string | null;
}

export interface FreeformActionRequest {
  user_input: string;
  rationale?: string;
  session_id?: string;
}

export async function postFreeformAction(
  req: FreeformActionRequest,
  init?: { signal?: AbortSignal },
): Promise<FreeformActionResponse> {
  const resp = await fetch(`${API_URL}/api/v2/freeform_action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    cache: "no-store",
    signal: init?.signal,
  });

  if (!resp.ok) {
    let detail = "";
    try {
      const data = await resp.json();
      detail =
        typeof data?.detail === "string"
          ? data.detail
          : JSON.stringify(data);
    } catch {
      detail = await resp.text();
    }
    throw new Error(`freeform_action ${resp.status}: ${detail}`);
  }

  return (await resp.json()) as FreeformActionResponse;
}

/**
 * 예측 생성 — 유휴 시간에 추천 버튼을 미리 생성(클릭 시 캐시 히트 0초).
 *
 * 한 턴을 그린 뒤 사용자가 읽는 동안 호출한다. 서버가 dry-run으로 미리 생성·캐시하고,
 * 실제 제출(postFreeformAction)이 캐시를 투명하게 확인한다. best-effort — 실패해도
 * 실 플레이에 무영향. 자유 입력은 예측 불가라 캐시 미스(기존 경로).
 */
export async function predictActions(
  sessionId: string,
  actions: string[],
  init?: { signal?: AbortSignal },
): Promise<void> {
  if (!sessionId || actions.length === 0) return;
  try {
    await fetch(`${API_URL}/api/v2/freeform_action/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, actions }),
      cache: "no-store",
      signal: init?.signal,
    });
  } catch {
    // 예측은 보조 — 실패 무시(실 플레이 무영향).
  }
}

export interface FreeformStreamHandlers {
  /** narrative 토큰 delta — 점진 노출용 */
  onToken?: (text: string) => void;
  /** canonical 최종 응답(시스템/clock/tip 포함) */
  onComplete?: (resp: FreeformActionResponse) => void;
  /** 스트림 처리 오류 */
  onError?: (detail: string) => void;
}

/**
 * 서빙 1단계 — SSE 토큰 점진 스트리밍 (POST /api/v2/freeform_action/stream).
 *
 * EventSource는 GET 전용이라 fetch + ReadableStream으로 SSE를 직접 파싱한다.
 * event: token  → onToken(delta) (점진 노출)
 * event: complete → onComplete(resp), 반환값으로도 전달 (상태 권위)
 * event: error → onError(detail)
 *
 * 반환: 최종 FreeformActionResponse (complete 미수신/오류 시 null).
 */
export async function streamFreeformAction(
  req: FreeformActionRequest,
  handlers: FreeformStreamHandlers,
  init?: { signal?: AbortSignal },
): Promise<FreeformActionResponse | null> {
  const resp = await fetch(`${API_URL}/api/v2/freeform_action/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    cache: "no-store",
    signal: init?.signal,
  });

  if (!resp.ok || resp.body === null) {
    let detail = "";
    try {
      detail = await resp.text();
    } catch {
      detail = `status ${resp.status}`;
    }
    throw new Error(`freeform_action/stream ${resp.status}: ${detail}`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let final: FreeformActionResponse | null = null;

  const handleFrame = (frame: string): void => {
    let event = "message";
    const dataLines: string[] = [];
    for (const line of frame.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
    }
    const data = dataLines.join("\n");
    if (data.length === 0) return;
    if (event === "token") {
      const obj = JSON.parse(data) as { text?: string };
      if (obj.text) handlers.onToken?.(obj.text);
    } else if (event === "complete") {
      final = JSON.parse(data) as FreeformActionResponse;
      handlers.onComplete?.(final);
    } else if (event === "error") {
      const obj = JSON.parse(data) as { detail?: string };
      handlers.onError?.(obj.detail ?? "stream error");
    }
  };

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      if (frame.trim().length > 0) handleFrame(frame);
    }
  }
  if (buffer.trim().length > 0) handleFrame(buffer);

  return final;
}
