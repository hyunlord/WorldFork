"use client";

/**
 * FighterCard — 파티 본격 (★ portrait + HP/혼력 + 정수 슬롯).
 *
 * Phase 6 combat_screen.html .fighter 정합.
 * 본문 정합: Character V2 soul_power 본격 mana proxy.
 */

const ESSENCE_COLOR_HEX: Record<string, string> = {
  빨강: "#c44d4d",
  파랑: "#4d7cc4",
  초록: "#5cb377",
  노랑: "#d4af37",
  흰색: "#e8e8d8",
  검정: "#2a2a2a",
};

interface EssenceLite {
  color?: string;
  name?: string;
}

interface FighterCardProps {
  name: string;
  portraitSrc: string;
  raceOrClass?: string;
  hp: number;
  hpMax: number;
  soulPower?: number;
  soulPowerMax?: number;
  essences?: EssenceLite[];
}

export function FighterCard({
  name,
  portraitSrc,
  raceOrClass,
  hp,
  hpMax,
  soulPower,
  soulPowerMax,
  essences = [],
}: FighterCardProps) {
  const hpPct = hpMax > 0 ? Math.max(0, Math.min(100, (hp / hpMax) * 100)) : 0;
  const showSoul =
    soulPower !== undefined &&
    soulPowerMax !== undefined &&
    soulPowerMax > 0;
  const soulPct = showSoul
    ? Math.max(0, Math.min(100, (soulPower / soulPowerMax) * 100))
    : 0;

  return (
    <div className="fighter-card">
      <div
        className="fighter-portrait"
        style={{ backgroundImage: `url(${portraitSrc})` }}
        role="img"
        aria-label={`${name} 액션`}
      />
      <div className="fighter-info">
        <div className="fighter-name">{name}</div>
        {raceOrClass && <div className="fighter-class">{raceOrClass}</div>}

        <div className="fighter-bar-label">
          <span>HP</span>
          <span>
            {hp}/{hpMax}
          </span>
        </div>
        <div className="fighter-bar">
          <div className="fill hp" style={{ width: `${hpPct}%` }} />
        </div>

        {showSoul && (
          <>
            <div className="fighter-bar-label">
              <span>혼력</span>
              <span>
                {soulPower}/{soulPowerMax}
              </span>
            </div>
            <div className="fighter-bar mana">
              <div className="fill" style={{ width: `${soulPct}%` }} />
            </div>
          </>
        )}

        {essences.length > 0 && (
          <div className="fighter-essences">
            {essences.map((e, i) => {
              const color = e.color ?? "";
              const hex = ESSENCE_COLOR_HEX[color];
              return (
                <div
                  key={i}
                  className="fighter-essence-orb"
                  style={
                    hex
                      ? { backgroundColor: hex, boxShadow: `0 0 8px ${hex}` }
                      : { backgroundColor: "#888" }
                  }
                  title={e.name ?? color}
                />
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
