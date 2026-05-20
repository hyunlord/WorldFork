import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { postFreeformAction } from "./freeform";

describe("postFreeformAction", () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("POST /api/v2/freeform_action 의 JSON body + headers 정합", async () => {
    const mockFetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          resolved_path: "fallback",
          matched_action: null,
          confidence: 0.18,
          narrative: "비요른은 잠시 멈춰 서서 주변을 살핍니다.",
          state_delta: {
            hp_change: 0,
            inventory_add: [],
            inventory_remove: [],
            location: null,
            time_advance: 1,
            affinity_changes: {},
          },
          fallback_reason: "자유 행동",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    globalThis.fetch = mockFetch;

    const resp = await postFreeformAction({
      user_input: "주변을 살핀다",
      rationale: "탐색",
    });

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/api\/v2\/freeform_action$/);
    expect(init.method).toBe("POST");
    const headers = init.headers as Record<string, string>;
    expect(headers["Content-Type"]).toBe("application/json");
    expect(JSON.parse(init.body as string)).toEqual({
      user_input: "주변을 살핀다",
      rationale: "탐색",
    });

    expect(resp.resolved_path).toBe("fallback");
    expect(resp.fallback_reason).toBe("자유 행동");
  });

  it("non-OK 응답 본 detail 본 포함한 Error throw", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "intent classifier failed" }), {
        status: 502,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(
      postFreeformAction({ user_input: "x" }),
    ).rejects.toThrow(/502.*intent classifier failed/);
  });
});
