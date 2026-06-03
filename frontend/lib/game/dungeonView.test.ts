import { describe, expect, it } from "vitest";

import type { GameStateV2 } from "@/lib/api/v2";

import { buildDungeonView } from "./dungeonView";

function makeState(over: Partial<GameStateV2>): GameStateV2 {
  return {
    characters: {},
    encounters: [],
    world: {
      active_rifts: [],
      party_members: [],
      hours_in_dungeon: 0,
      is_dark_zone: false,
    },
    location: {
      realm: "라스카니아",
      floor: 1,
      sub_area: "수정동굴",
      rift_id: null,
      visibility_meters: 10,
      has_light: true,
    },
    ...over,
  } as GameStateV2;
}

function tileTypes(view: ReturnType<typeof buildDungeonView>): string[] {
  if (!view) return [];
  return view.rows.flat().map((t) => t.type);
}

describe("buildDungeonView", () => {
  it("state 없으면 null (★ mock fallback 금지 — 호출자가 로딩 표시)", () => {
    expect(buildDungeonView(null, 3)).toBeNull();
  });

  it("마을(floor 0)이면 null (DungeonView 미사용)", () => {
    expect(buildDungeonView(makeState({ location: makeState({}).location }), 3)).not.toBeNull();
    const village = makeState({});
    village.location = { ...village.location, floor: 0 };
    expect(buildDungeonView(village, 3)).toBeNull();
  });

  it("실 encounters의 적대 수만큼 enemy 타일 (★ 가짜 X)", () => {
    const state = makeState({
      encounters: [
        { name: "고블린", hostile: true, enemy_type: "physical" },
        { name: "슬라임", hostile: true, enemy_type: "physical" },
        { name: "부족장", hostile: false }, // 비적대 — 적으로 안 셈
      ],
    });
    const view = buildDungeonView(state, 5);
    const types = tileTypes(view);
    expect(types.filter((t) => t === "enemy")).toHaveLength(2);
    expect(types.filter((t) => t === "player")).toHaveLength(1);
    // 범례도 실 적 수 반영
    expect(view?.legend?.some((l) => l.label.includes("×2"))).toBe(true);
  });

  it("적 0이면 enemy 타일 0 (★ mock 적 위장 X) — 본인/계단만", () => {
    const view = buildDungeonView(makeState({ encounters: [] }), 2);
    const types = tileTypes(view);
    expect(types.filter((t) => t === "enemy")).toHaveLength(0);
    expect(types.filter((t) => t === "player")).toHaveLength(1);
    expect(types.filter((t) => t === "stair")).toHaveLength(1);
  });

  it("turn은 실 값 그대로 (★ DEMO 142 mock 아님)", () => {
    const view = buildDungeonView(makeState({}), 7);
    expect(view?.turn).toBe(7);
  });

  it("적이 많아도 표시 상한 내 — 본인 타일 보존", () => {
    const many = Array.from({ length: 12 }, (_, i) => ({
      name: `적${i}`,
      hostile: true,
    }));
    const view = buildDungeonView(makeState({ encounters: many }), 9);
    const types = tileTypes(view);
    expect(types.filter((t) => t === "enemy").length).toBeLessThanOrEqual(6);
    expect(types.filter((t) => t === "player")).toHaveLength(1);
  });
});
