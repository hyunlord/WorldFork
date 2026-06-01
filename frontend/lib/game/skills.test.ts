import { describe, expect, it } from "vitest";

import { collectEssenceSkills, skillMeta } from "./skills";

describe("collectEssenceSkills", () => {
  it("흡수 정수의 active/passive skill 추출", () => {
    const player = {
      essences: [
        {
          name: "고블린 정수",
          active_skills: [
            { name: "도둑걸음", type: "액티브", description: "은신", soul_cost: 10 },
          ],
          passive_skills: [
            { name: "독화살", type: "패시브", description: "독 부여" },
          ],
        },
      ],
    };
    const rows = collectEssenceSkills(player);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatchObject({ name: "도둑걸음", kind: "active", soulCost: 10, source: "고블린 정수" });
    expect(rows[1]).toMatchObject({ name: "독화살", kind: "passive", soulCost: null });
  });

  it("essences 없으면 빈 배열", () => {
    expect(collectEssenceSkills({})).toEqual([]);
    expect(collectEssenceSkills(null)).toEqual([]);
    expect(collectEssenceSkills({ essences: [] })).toEqual([]);
  });

  it("skill 필드 누락 시 안전 기본값", () => {
    const rows = collectEssenceSkills({ essences: [{ active_skills: [{}] }] });
    expect(rows[0]).toMatchObject({ name: "스킬", kind: "active", soulCost: null, source: "정수" });
  });

  it("여러 정수의 skill 합집합", () => {
    const player = {
      essences: [
        { name: "A", active_skills: [{ name: "a1" }] },
        { name: "B", passive_skills: [{ name: "b1" }, { name: "b2" }] },
      ],
    };
    expect(collectEssenceSkills(player)).toHaveLength(3);
  });
});

describe("skillMeta", () => {
  it("active + 영혼력 표기", () => {
    expect(
      skillMeta({ name: "x", kind: "active", description: "", soulCost: 20, source: "s" }),
    ).toBe("액티브 · 영혼력 20");
  });

  it("active 영혼력 없으면 액티브만", () => {
    expect(
      skillMeta({ name: "x", kind: "active", description: "", soulCost: null, source: "s" }),
    ).toBe("액티브");
  });

  it("passive는 패시브", () => {
    expect(
      skillMeta({ name: "x", kind: "passive", description: "", soulCost: null, source: "s" }),
    ).toBe("패시브");
  });
});
