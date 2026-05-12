"use client";

/**
 * StatsPanel — Character V2 stats 본격 (★ state_v2.py 정합).
 *
 * 본문 본격 mapping:
 * - HP: hp / hp_max
 * - 메인 3대: physical / mental / special
 * - 1티어: strength / agility / flexibility
 * - 운: luck
 * - 방어 본격: bone_strength / durability
 */

import type { CharacterV2 } from "@/lib/api/v2";

interface StatRow {
  label: string;
  value: number | string;
}

interface StatsPanelProps {
  character: CharacterV2;
}

function num(value: unknown): number | undefined {
  return typeof value === "number" ? value : undefined;
}

export function StatsPanel({ character }: StatsPanelProps) {
  const hp = num(character.hp) ?? 0;
  const hpMax = num(character.hp_max) ?? 0;
  const hpPct =
    hpMax > 0 ? Math.max(0, Math.min(100, (hp / hpMax) * 100)) : 0;

  const stats: StatRow[] = [
    { label: "육체 (Physical)", value: num(character.physical) ?? "—" },
    { label: "정신 (Mental)", value: num(character.mental) ?? "—" },
    { label: "이능 (Special)", value: num(character.special) ?? "—" },
    { label: "근력 (STR)", value: num(character.strength) ?? "—" },
    { label: "민첩 (AGI)", value: num(character.agility) ?? "—" },
    { label: "유연성 (FLEX)", value: num(character.flexibility) ?? "—" },
    { label: "골강도 (DEF)", value: num(character.bone_strength) ?? "—" },
    { label: "내구력", value: num(character.durability) ?? "—" },
    { label: "회피율", value: num(character.evasion) ?? "—" },
    { label: "행운 (LUCK)", value: num(character.luck) ?? "—" },
  ];

  return (
    <div className="stats-panel">
      <div className="panel-title">▣ 능력치</div>
      <div className="hp-block">
        <div className="hp-block-label">
          <span>HP</span>
          <span className="hp-block-value">
            {hp} / {hpMax}
          </span>
        </div>
        <div className="hp-bar-large">
          <div className="hp-fill-large" style={{ width: `${hpPct}%` }} />
        </div>
      </div>
      <div className="stats-grid">
        {stats.map((s) => (
          <div key={s.label} className="stat-row">
            <span className="stat-row-label">{s.label}</span>
            <span className="stat-row-value">{s.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
