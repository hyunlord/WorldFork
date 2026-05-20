"use client";

import { useCallback, useRef, useState } from "react";

import {
  postFreeformAction,
  type FreeformActionResponse,
} from "@/lib/api/freeform";
import {
  getStoredSessionId,
  setStoredSessionId,
} from "@/lib/session";

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
 * Phase D step 4 — session_id 통합 자연어 input hook.
 *
 * - localStorage에 저장된 session_id를 매 요청에 첨부
 * - 응답의 session_id를 localStorage에 갱신
 * - AbortController로 in-flight 중복 요청 취소
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
        const sessionId = getStoredSessionId();
        const resp = await postFreeformAction(
          {
            user_input: userInput,
            rationale,
            ...(sessionId !== null ? { session_id: sessionId } : {}),
          },
          { signal: controller.signal },
        );
        if (controller.signal.aborted) return null;
        if (resp.session_id !== null) {
          setStoredSessionId(resp.session_id);
        }
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
