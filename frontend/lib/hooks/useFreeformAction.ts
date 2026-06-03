"use client";

import { useCallback, useRef, useState } from "react";

import {
  streamFreeformAction,
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
  /** 스트리밍 중 누적 narrative 미리보기 (완료 시 "" 로 비움) */
  streamingText: string;
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
  const [streamingText, setStreamingText] = useState("");
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
      setStreamingText("");
      let streamErr: string | null = null;
      try {
        const sessionId = getStoredSessionId();
        const resp = await streamFreeformAction(
          {
            user_input: userInput,
            rationale,
            ...(sessionId !== null ? { session_id: sessionId } : {}),
          },
          {
            // ★ 토큰 점진 노출 — ~0.2초 시작(통째 대기 제거)
            onToken: (text) => {
              if (!controller.signal.aborted) {
                setStreamingText((prev) => prev + text);
              }
            },
            onError: (detail) => {
              streamErr = detail;
            },
          },
          { signal: controller.signal },
        );
        if (controller.signal.aborted) return null;
        if (streamErr !== null) {
          setError(streamErr);
          setStreamingText("");
          return null;
        }
        if (resp !== null && resp.session_id !== null) {
          setStoredSessionId(resp.session_id);
        }
        if (resp !== null) {
          setLastResponse(resp);
        }
        // 완료 — 미리보기는 비우고, 호출자가 canonical narrative를 히스토리에 누적
        setStreamingText("");
        return resp;
      } catch (e) {
        if (controller.signal.aborted) return null;
        const msg = e instanceof Error ? e.message : String(e);
        setError(msg);
        setStreamingText("");
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
    setStreamingText("");
  }, []);

  return { loading, error, lastResponse, streamingText, submit, reset };
}
