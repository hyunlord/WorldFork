import { afterEach, describe, expect, it, vi } from "vitest";

import {
  postFreeformAction,
  streamFreeformAction,
  type FreeformActionResponse,
} from "./freeform";

/** SSE 바이트 스트림을 흉내내는 Response (ReadableStream body). */
function sseResponse(frames: string[]): Response {
  const enc = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const f of frames) controller.enqueue(enc.encode(f));
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

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

describe("streamFreeformAction (SSE)", () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  const COMPLETE: FreeformActionResponse = {
    resolved_path: "intent",
    matched_action: "dialogue",
    confidence: 0.92,
    narrative: "부족장은 내 말을 듣고 고개를 끄덕인다.",
    state_delta: {
      hp_change: 0,
      inventory_add: [],
      inventory_remove: [],
      location: null,
      time_advance: 1,
      affinity_changes: {},
    },
    fallback_reason: null,
    session_id: "sess-1",
    session_state: null,
  };

  it("token 점진 + complete 파싱 — POST /stream 엔드포인트", async () => {
    const frames = [
      `event: token\ndata: ${JSON.stringify({ text: "부족장은 " })}\n\n`,
      // 한 프레임이 여러 청크로 쪼개져 와도 누적 파싱
      `event: token\ndata: ${JSON.stringify({ text: "내 " })}\n\n` +
        `event: token\ndata: ${JSON.stringify({ text: "말을 듣는다." })}\n\n`,
      `event: complete\ndata: ${JSON.stringify(COMPLETE)}\n\n`,
    ];
    const mockFetch = vi.fn().mockResolvedValue(sseResponse(frames));
    globalThis.fetch = mockFetch;

    const tokens: string[] = [];
    const final = await streamFreeformAction(
      { user_input: "부족장에게 말을 건다", session_id: "sess-1" },
      { onToken: (t) => tokens.push(t) },
    );

    const [url] = mockFetch.mock.calls[0] as [string];
    expect(url).toMatch(/\/api\/v2\/freeform_action\/stream$/);
    expect(tokens).toEqual(["부족장은 ", "내 ", "말을 듣는다."]);
    expect(final?.matched_action).toBe("dialogue");
    expect(final?.narrative).toContain("고개를 끄덕인다");
  });

  it("error 이벤트 → onError 호출 + null 반환", async () => {
    globalThis.fetch = vi
      .fn()
      .mockResolvedValue(
        sseResponse([
          `event: error\ndata: ${JSON.stringify({ detail: "boom" })}\n\n`,
        ]),
      );

    let errDetail = "";
    const final = await streamFreeformAction(
      { user_input: "x" },
      { onError: (d) => (errDetail = d) },
    );

    expect(errDetail).toBe("boom");
    expect(final).toBe(null);
  });

  it("non-OK 응답 → Error throw", async () => {
    globalThis.fetch = vi
      .fn()
      .mockResolvedValue(new Response("dead", { status: 502 }));

    await expect(
      streamFreeformAction({ user_input: "x" }, {}),
    ).rejects.toThrow(/stream 502/);
  });
});
