/**
 * 흡수 정수 → magic·skill 표시 추출.
 *
 * backend가 흡수한 정수마다 active_skills / passive_skills(state_v2.Skill)를
 * state로 직렬화한다(state_v2_serialize). 이 skill은 게임에서 이미 발동된다:
 * - active → handle_attack의 active skill bonus (_compute_player_attack)
 * - passive → 자연 재생 등 passive 효과 (effects.classify_skill)
 *
 * 캐릭터 시트는 그동안 race trait만 보여줘 흡수로 얻은 magic·skill이 화면에
 * 닿지 않았다. 이 모듈이 essences에서 발동 skill을 뽑아 노출한다.
 */

export interface EssenceSkillRow {
  name: string;
  kind: "active" | "passive";
  description: string;
  soulCost: number | null;
  /** 출처 정수 이름 */
  source: string;
}

// SkillType.value (state_v2.SkillType) — 액티브/패시브 한글 enum value.
const ACTIVE_LABEL = "액티브";

function toRows(
  raw: unknown,
  kind: "active" | "passive",
  source: string,
): EssenceSkillRow[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((s) => {
    const skill = (s ?? {}) as Record<string, unknown>;
    const cost = skill.soul_cost;
    return {
      name: String(skill.name ?? "스킬"),
      kind,
      description: String(skill.description ?? ""),
      soulCost: typeof cost === "number" ? cost : null,
      source,
    };
  });
}

/** player의 흡수 정수에서 active/passive skill 행을 모은다. */
export function collectEssenceSkills(
  player: Record<string, unknown> | null,
): EssenceSkillRow[] {
  if (!player) return [];
  const essencesRaw = player.essences;
  if (!Array.isArray(essencesRaw)) return [];

  const rows: EssenceSkillRow[] = [];
  for (const e of essencesRaw) {
    const ess = (e ?? {}) as Record<string, unknown>;
    const source = String(ess.name ?? "정수");
    // active_skills를 type value로 한 번 더 거르지 않는다 — backend가 이미
    // active_skills/passive_skills로 분리해 직렬화하므로 그대로 신뢰.
    rows.push(...toRows(ess.active_skills, "active", source));
    rows.push(...toRows(ess.passive_skills, "passive", source));
  }
  return rows;
}

/** active skill의 메타 표기 (영혼력 소모 포함). */
export function skillMeta(row: EssenceSkillRow): string {
  if (row.kind !== "active") return "패시브";
  return row.soulCost != null ? `${ACTIVE_LABEL} · 영혼력 ${row.soulCost}` : ACTIVE_LABEL;
}
