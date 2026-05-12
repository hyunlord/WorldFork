"use client";

/**
 * usePostAction — POST /api/v2/action 본격 mutation hook (★ Phase 7k).
 *
 * 본 hook 본격:
 * - executing / lastResult / error 본격
 * - execute(req) 본격 Promise<ActionResponse | null>
 * - 모든 화면 본격 공통 활용 (★ Game/Rift/Combat/Dialogue)
 */

import { useCallback, useState } from "react";

import {
  postAction,
  type ActionRequest,
  type ActionResponse,
} from "@/lib/api/v2";

export interface UsePostActionResult {
  executing: boolean;
  lastResult: ActionResponse | null;
  error: Error | null;
  execute: (req: ActionRequest) => Promise<ActionResponse | null>;
}

export function usePostAction(): UsePostActionResult {
  const [executing, setExecuting] = useState(false);
  const [lastResult, setLastResult] = useState<ActionResponse | null>(null);
  const [error, setError] = useState<Error | null>(null);

  const execute = useCallback(
    async (req: ActionRequest): Promise<ActionResponse | null> => {
      setExecuting(true);
      setError(null);
      try {
        const result = await postAction(req);
        setLastResult(result);
        return result;
      } catch (e) {
        setError(e instanceof Error ? e : new Error(String(e)));
        return null;
      } finally {
        setExecuting(false);
      }
    },
    []
  );

  return { executing, lastResult, error, execute };
}
