"use client";

/**
 * useGameState — session 기반 Tier 2 state hook (★ harness 재설계).
 *
 * 직전: GET /api/v2/state (global default 투르윈+실렌 — 잘못된 잔재).
 * 재설계: 저장된 session_id로 GET /api/v2/session/{id}/state → 어댑터.
 *   세션 없으면 명시 에러 (DEMO fallback 위장 금지).
 */

import { useCallback, useEffect, useState } from "react";

import {
  fetchSessionState,
  sessionToStateResponse,
  type StateResponse,
} from "@/lib/api/v2";
import { getStoredSessionId } from "@/lib/session";

export interface UseGameStateResult {
  data: StateResponse | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export function useGameState(): UseGameStateResult {
  const [data, setData] = useState<StateResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const sessionId = getStoredSessionId();
      if (!sessionId) {
        // ★ DEMO fallback 금지 — 세션 없으면 명시 에러 (위장 X)
        throw new Error("세션 없음 — 캐릭터를 먼저 생성하세요");
      }
      const session = await fetchSessionState(sessionId);
      setData(sessionToStateResponse(session));
    } catch (e) {
      setData(null);
      setError(e instanceof Error ? e : new Error(String(e)));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { data, loading, error, refetch };
}
