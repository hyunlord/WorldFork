"use client";

import { useCallback, useRef, useState } from "react";

import {
  postFreeformAction,
  type FreeformActionResponse,
} from "@/lib/api/freeform";

export interface UseFreeformActionResult {
  loading: boolean;
  error: string | null;
  lastResponse: FreeformActionResponse | null;
  submit: (
    userInput: string,
    rationale?: string,
  ) => Promise<FreeformActionResponse | null>;
  reset: () => void;
}

/**
 * Phase D — 자연어 input → /api/v2/freeform_action hook.
 *
 * - loading / error / lastResponse 본 state expose
 * - submit 본 사용자 input + optional rationale 본 호출
 * - 직전 in-flight request 본 AbortController 본 cancel (★ rapid submit 시
 *   stale response 방지)
 */
export function useFreeformAction(): UseFreeformActionResult {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResponse, setLastResponse] =
    useState<FreeformActionResponse | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const submit = useCallback(
    async (
      userInput: string,
      rationale?: string,
    ): Promise<FreeformActionResponse | null> => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setLoading(true);
      setError(null);
      try {
        const resp = await postFreeformAction(
          { user_input: userInput, rationale },
          { signal: controller.signal },
        );
        if (controller.signal.aborted) return null;
        setLastResponse(resp);
        return resp;
      } catch (e) {
        if (controller.signal.aborted) return null;
        const msg = e instanceof Error ? e.message : String(e);
        setError(msg);
        return null;
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    },
    [],
  );

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setLoading(false);
    setError(null);
    setLastResponse(null);
  }, []);

  return { loading, error, lastResponse, submit, reset };
}
