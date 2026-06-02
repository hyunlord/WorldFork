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
