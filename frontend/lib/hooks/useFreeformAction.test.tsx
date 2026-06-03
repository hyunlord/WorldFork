import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as freeformApi from "@/lib/api/freeform";
import type {
  FreeformActionResponse,
  FreeformStreamHandlers,
} from "@/lib/api/freeform";

import { useFreeformAction } from "./useFreeformAction";

const ATTACK_RESP: FreeformActionResponse = {
  resolved_path: "intent",
  matched_action: "attack",
  confidence: 0.95,
  narrative: "비요른은 공격을 시도합니다.",
  state_delta: {
    hp_change: 0,
    inventory_add: [],
    inventory_remove: [],
    location: null,
    time_advance: 1,
    affinity_changes: {},
  },
  fallback_reason: null,
  session_id: null,
  session_state: null,
};

describe("useFreeformAction", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("스트리밍 토큰 → lastResponse 등재 + 완료 후 streamingText 비움", async () => {
    const stub = vi
      .spyOn(freeformApi, "streamFreeformAction")
      .mockImplementation(
        async (_req, handlers: FreeformStreamHandlers) => {
          // ★ 토큰 점진 전달 후 canonical 최종 응답 반환
          handlers.onToken?.("비요른은 ");
          handlers.onToken?.("공격을 시도합니다.");
          handlers.onComplete?.(ATTACK_RESP);
          return ATTACK_RESP;
        },
      );

    const { result } = renderHook(() => useFreeformAction());

    expect(result.current.loading).toBe(false);
    expect(result.current.lastResponse).toBe(null);
    expect(result.current.streamingText).toBe("");

    await act(async () => {
      await result.current.submit("고블린을 공격");
    });

    expect(stub).toHaveBeenCalledWith(
      { user_input: "고블린을 공격", rationale: undefined },
      expect.objectContaining({ onToken: expect.any(Function) }),
      expect.objectContaining({ signal: expect.anything() }),
    );
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.lastResponse?.matched_action).toBe("attack");
    expect(result.current.error).toBe(null);
    // 완료 후 미리보기는 비워지고 호출자가 canonical narrative를 누적
    expect(result.current.streamingText).toBe("");
  });

  it("스트림 error 이벤트 → error state 등재 + lastResponse null 유지", async () => {
    vi.spyOn(freeformApi, "streamFreeformAction").mockImplementation(
      async (_req, handlers: FreeformStreamHandlers) => {
        handlers.onError?.("freeform_action 502: classifier dead");
        return null;
      },
    );

    const { result } = renderHook(() => useFreeformAction());

    await act(async () => {
      await result.current.submit("x");
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.error).toMatch(/502.*classifier dead/);
    expect(result.current.lastResponse).toBe(null);
    expect(result.current.streamingText).toBe("");
  });

  it("HTTP 거부(throw) → error state 등재", async () => {
    vi.spyOn(freeformApi, "streamFreeformAction").mockRejectedValue(
      new Error("freeform_action/stream 502: dead"),
    );

    const { result } = renderHook(() => useFreeformAction());

    await act(async () => {
      await result.current.submit("x");
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.error).toMatch(/502.*dead/);
    expect(result.current.lastResponse).toBe(null);
  });

  it("reset 본 모든 state clear", async () => {
    vi.spyOn(freeformApi, "streamFreeformAction").mockImplementation(
      async (_req, handlers: FreeformStreamHandlers) => {
        handlers.onComplete?.(ATTACK_RESP);
        return ATTACK_RESP;
      },
    );

    const { result } = renderHook(() => useFreeformAction());

    await act(async () => {
      await result.current.submit("주변");
    });
    expect(result.current.lastResponse).not.toBe(null);

    act(() => {
      result.current.reset();
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe(null);
    expect(result.current.lastResponse).toBe(null);
    expect(result.current.streamingText).toBe("");
  });
});
