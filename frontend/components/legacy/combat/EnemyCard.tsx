"use client";

/**
 * EnemyCard — 적 본격 (★ Encounter 본격 monster).
 *
 * Phase 6 combat_screen.html .enemy 정합.
 */

interface EnemyCardProps {
  name?: string;
  imageSrc: string;
  hp: number;
  hpMax: number;
  grade?: number | string;
  status?: string;
}

export function EnemyCard({
  name,
  imageSrc,
  hp,
  hpMax,
  grade,
  status,
}: EnemyCardProps) {
  const pct = hpMax > 0 ? Math.max(0, Math.min(100, (hp / hpMax) * 100)) : 0;

  return (
    <div className="enemy-card">
      <div
        className="enemy-portrait"
        style={{ backgroundImage: `url(${imageSrc})` }}
        role="img"
        aria-label={`${name ?? "적"} 이미지`}
      />
      <div className="enemy-name">{name ?? "미상"}</div>
      {grade !== undefined && (
        <div className="enemy-grade">{grade}등급</div>
      )}
      <div className="enemy-hp-bar">
        <div className="fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="enemy-hp-label">
        HP {hp}/{hpMax}
      </div>
      {status && <div className="enemy-status">상태: {status}</div>}
    </div>
  );
}
