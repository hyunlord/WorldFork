import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as freeformApi from "@/lib/api/freeform";

import { useFreeformAction } from "./useFreeformAction";

describe("useFreeformAction", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("loading → success 본 transition + lastResponse 등재", async () => {
    const stub = vi.spyOn(freeformApi, "postFreeformAction").mockResolvedValue({
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
    });

    const { result } = renderHook(() => useFreeformAction());

    expect(result.current.loading).toBe(false);
    expect(result.current.lastResponse).toBe(null);

    await act(async () => {
      await result.current.submit("고블린을 공격");
    });

    expect(stub).toHaveBeenCalledWith(
      { user_input: "고블린을 공격", rationale: undefined },
      expect.objectContaining({ signal: expect.anything() }),
    );
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.lastResponse?.matched_action).toBe("attack");
    expect(result.current.error).toBe(null);
  });

  it("API 오류 본 error state 등재 + lastResponse null 유지", async () => {
    vi.spyOn(freeformApi, "postFreeformAction").mockRejectedValue(
      new Error("freeform_action 502: classifier dead"),
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
  });

  it("reset 본 모든 state clear", async () => {
    vi.spyOn(freeformApi, "postFreeformAction").mockResolvedValue({
      resolved_path: "fallback",
      matched_action: null,
      confidence: 0.1,
      narrative: "주변을 살핀다.",
      state_delta: {
        hp_change: 0,
        inventory_add: [],
        inventory_remove: [],
        location: null,
        time_advance: 1,
        affinity_changes: {},
      },
      fallback_reason: "자유 행동",
    });

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
  });
});
