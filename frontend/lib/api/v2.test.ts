import { describe, expect, it } from "vitest";

import { sessionToStateResponse } from "./v2";
import type { SessionStateResponse } from "./v2";

/**
 * 진행 시스템(영혼력/LV/정수 슬롯) frontend 연결 회귀 테스트.
 *
 * 배경: manual play에서 진행이 0/LV1/0 고정으로 노출. 근본 원인은
 * sessionToStateResponse 어댑터가 player에 soul_power/player_level/max_essences/
 * essences를 매핑하지 않아 statusData가 default(0/1)로 떨어진 것. statusData는
 * player.soul_power / player.level / player.essences / player.max_essences 키를
 * 읽으므로 어댑터가 그 키로 매핑해야 한다(absorbed_essences ↔ essences 정합 포함).
 */
function baseSession(over: Record<string, unknown> = {}): SessionStateResponse {
  return {
    session_id: "s1",
    current_hp: 120,
    max_hp: 120,
    inventory: ["방패"],
    location: "라스카니아 · 부족 성지",
    turn_count: 0,
    floor_number: 0,
    hours_in_dungeon: 0,
    race: "barbarian",
    scenario_mode: "bjorn",
    absorbed_essences: [],
    rift_id: null,
    encounters: [],
    player_level: 1,
    player_xp: 0,
    max_essences: 1,
    soul_power: 10,
    ...over,
  } as SessionStateResponse;
}

function playerOf(s: SessionStateResponse): Record<string, unknown> {
  const st = sessionToStateResponse(s);
  return Object.values(st.state.characters)[0] as unknown as Record<
    string,
    unknown
  >;
}

describe("sessionToStateResponse — 진행 시스템 매핑 (영혼력/LV/정수)", () => {
  it("시작 진행 — 영혼력 10·LV 1·정수 0/1 (statusData 키 정합)", () => {
    const player = playerOf(baseSession());
    // statusData가 읽는 키: soul_power / level / essences / max_essences
    expect(player.soul_power).toBe(10);
    expect(player.level).toBe(1);
    expect(player.max_essences).toBe(1);
    expect(Array.isArray(player.essences)).toBe(true);
    expect((player.essences as unknown[]).length).toBe(0);
  });

  it("흡수 후 — 영혼력·LV·정수 증가 반영", () => {
    const player = playerOf(
      baseSession({
        soul_power: 25,
        player_level: 2,
        max_essences: 2,
        absorbed_essences: [{ name: "고블린 정수" }, { name: "늑대 정수" }],
      }),
    );
    expect(player.soul_power).toBe(25);
    expect(player.level).toBe(2);
    expect(player.max_essences).toBe(2);
    expect((player.essences as unknown[]).length).toBe(2);
  });

  it("회귀 방지 — 어댑터가 soul_power 매핑 (undefined → 0 고정 버그)", () => {
    const player = playerOf(baseSession({ soul_power: 10 }));
    expect(player.soul_power).not.toBeUndefined();
    expect(player.soul_power).toBe(10);
  });

  it("essences 키 정합 — absorbed_essences ↔ statusData essences", () => {
    const player = playerOf(
      baseSession({ absorbed_essences: [{ name: "정수A" }] }),
    );
    // statusData는 player.essences를 읽음 — 어댑터 absorbed_essences와 동일 데이터
    expect(player.essences).toEqual(player.absorbed_essences);
    expect((player.essences as unknown[]).length).toBe(1);
  });
});
