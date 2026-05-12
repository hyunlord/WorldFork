"use client";

/**
 * SkillsPanel — 정수 본격 active + passive skills 본격.
 *
 * 본격 본질: character.essences[].active_skills + .passive_skills
 * - name, type (ACTIVE/PASSIVE), description
 * - soul_cost / cooldown_seconds (액티브만)
 *
 * Phase 6 character_sheet.html .skill 정합.
 */

interface SkillDef {
  name?: string;
  type?: string;
  description?: string;
  soul_cost?: number | null;
  cooldown_seconds?: number | null;
}

interface EssenceEntry {
  active_skills?: SkillDef[];
  passive_skills?: SkillDef[];
}

interface SkillsPanelProps {
  essences: EssenceEntry[];
}

function iconFor(skill: SkillDef): string {
  const name = skill.name ?? "?";
  return name.slice(0, 1);
}

export function SkillsPanel({ essences }: SkillsPanelProps) {
  const allSkills: SkillDef[] = [];
  for (const e of essences) {
    for (const s of e.active_skills ?? []) allSkills.push(s);
    for (const s of e.passive_skills ?? []) allSkills.push(s);
  }

  return (
    <div className="skills-panel">
      <div className="panel-title">▣ 스킬</div>
      {allSkills.length === 0 ? (
        <div className="empty-message">아직 습득한 스킬이 없다.</div>
      ) : (
        <div className="skills-list">
          {allSkills.map((s, i) => (
            <div key={i} className="skill">
              <div className="skill-icon">{iconFor(s)}</div>
              <div className="skill-info">
                <div className="skill-name">
                  {s.name ?? "?"}
                  {s.type && (
                    <span className="skill-type">{` (${s.type})`}</span>
                  )}
                </div>
                {s.description && (
                  <div className="skill-desc">{s.description}</div>
                )}
                {(s.soul_cost ?? null) !== null && (
                  <div className="skill-meta">
                    Soul {s.soul_cost}
                    {s.cooldown_seconds != null
                      ? ` · CD ${s.cooldown_seconds}s`
                      : ""}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
