"use client";

import { useEffect, useRef } from "react";

export interface KeyboardOptions {
  enabled?: boolean;
  ignoreWhenInput?: boolean;
}

export type KeyboardHandler = (
  key: string,
  event: KeyboardEvent,
) => void;

/**
 * 키보드 단축키 hook.
 *
 * - 한국어 IME 안전: `isComposing` true 면 무시
 * - 자연어 input 에 포커스가 있으면 단축키 disable (★ ignoreWhenInput=true 기본)
 * - Esc 만 INPUT 위에서도 허용
 */
export function useKeyboard(
  handler: KeyboardHandler,
  options: KeyboardOptions = {},
) {
  const { enabled = true, ignoreWhenInput = true } = options;
  const handlerRef = useRef(handler);

  useEffect(() => {
    handlerRef.current = handler;
  }, [handler]);

  useEffect(() => {
    if (!enabled || typeof window === "undefined") return;

    const onKey = (e: KeyboardEvent) => {
      if (e.isComposing) return;
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName?.toUpperCase();
      const isEditable =
        tag === "INPUT" ||
        tag === "TEXTAREA" ||
        (target?.isContentEditable ?? false);

      if (isEditable && ignoreWhenInput) {
        if (e.key === "Escape") {
          handlerRef.current(e.key, e);
        }
        return;
      }

      handlerRef.current(e.key, e);
    };

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [enabled, ignoreWhenInput]);
}
