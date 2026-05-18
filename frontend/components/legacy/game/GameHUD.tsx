"use client";

/**
 * GameHUD — 좌상단 HUD (★ HP bars + 빛 자원).
 *
 * Phase 6 gameplay_screen.html .hud-left 정합.
 */

import type { CharacterV2 } from "@/lib/api/v2";

interface HPBarProps {
  name: string;
  hp: number;
  maxHp: number;
}

function HPBar({ name, hp, maxHp }: HPBarProps) {
  const percentage =
    maxHp > 0 ? Math.max(0, Math.min(100, (hp / maxHp) * 100)) : 0;
  return (
    <div className="hp-bar-row">
      <div className="hp-label">
        <span>{name}</span>
        <span className="hp-value">
          {hp}/{maxHp}
        </span>
      </div>
      <div className="hp-bar">
        <div className="hp-fill" style={{ width: `${percentage}%` }} />
      </div>
    </div>
  );
}

interface LightStateLite {
  active_source_name?: string | null;
  remaining_duration_hours?: number;
}

interface LightSummaryProps {
  characters: Record<string, CharacterV2>;
}

function LightSummary({ characters }: LightSummaryProps) {
  // 본격 본질: 캐릭터별 active 본격 카운트 (★ ON 점등)
  const slots = Object.values(characters).map((c) => {
    const ls = (c.light_state ?? {}) as LightStateLite;
    return Boolean(
      ls.active_source_name &&
        (ls.remaining_duration_hours ?? 0) > 0
    );
  });
  // 본격 padding (★ 최소 6 자리 — 시각 정합)
  while (slots.length < 6) slots.push(false);

  const active = slots.filter(Boolean).length;
  const total = slots.length;

  return (
    <div className="light-charges-row">
      <div className="hp-label">
        <span>빛 자원</span>
        <span className="hp-value">
          {active}/{total}
        </span>
      </div>
      <div className="light-charges">
        {slots.map((on, i) => (
          <div
            key={i}
            className={`light-charge${on ? "" : " spent"}`}
          />
        ))}
      </div>
    </div>
  );
}

interface GameHUDProps {
  characters: Record<string, CharacterV2>;
}

export function GameHUD({ characters }: GameHUDProps) {
  return (
    <div className="game-hud-left">
      {Object.entries(characters).map(([name, c]) => (
        <HPBar
          key={name}
          name={name}
          hp={typeof c.hp === "number" ? c.hp : 0}
          maxHp={typeof c.hp_max === "number" ? c.hp_max : 0}
        />
      ))}
      <LightSummary characters={characters} />
    </div>
  );
}
