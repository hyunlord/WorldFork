"use client";

/**
 * CombatHeader — 라운드 + 위치.
 *
 * Phase 6 combat_screen.html .header 정합.
 */

interface CombatHeaderProps {
  round?: number;
  locationLabel?: string | null;
}

export function CombatHeader({
  round = 1,
  locationLabel,
}: CombatHeaderProps) {
  return (
    <div className="combat-header">
      <div className="round-num">— 라운드 {round} —</div>
      {locationLabel && (
        <div className="combat-location-name">{locationLabel}</div>
      )}
    </div>
  );
}
