"use client";

/**
 * useGameState — Tier 2 state 본격 React hook (★ Phase 7b).
 *
 * 본 hook 본격:
 * - 본격 GET /api/v2/state fetch
 * - loading / error / data / refetch 본격
 */

import { useCallback, useEffect, useState } from "react";

import {
  fetchCurrentState,
  type StateResponse,
} from "@/lib/api/v2";

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
      const result = await fetchCurrentState();
      setData(result);
    } catch (e) {
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
