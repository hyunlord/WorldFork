"use client";

/**
 * useRecentActions — 최근 N 행동 본격 hook (★ Phase 7d).
 *
 * GET /api/v2/state/recent_actions?n=N 본격.
 */

import { useCallback, useEffect, useState } from "react";

import {
  fetchRecentActions,
  type RecentActionsResponse,
} from "@/lib/api/v2";

export interface UseRecentActionsResult {
  data: RecentActionsResponse | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export function useRecentActions(n: number = 5): UseRecentActionsResult {
  const [data, setData] = useState<RecentActionsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchRecentActions(n);
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e : new Error(String(e)));
    } finally {
      setLoading(false);
    }
  }, [n]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { data, loading, error, refetch };
}
